#!/usr/bin/env python3
"""Working script to fix TRY003 violations by extracting long error messages to variables."""

import json
import re
import subprocess
from pathlib import Path
from typing import Any


def get_try003_violations(file_path: Path) -> list[dict[str, Any]]:
    """Get TRY003 violations for a specific file using ruff."""
    try:
        result = subprocess.run(
            [
                "/usr/local/python/current/bin/poetry",
                "run",
                "ruff",
                "check",
                "--select",
                "TRY003",
                "--output-format=json",
                str(file_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd="/workspaces/data-fetcher-sftp",
        )

        if result.returncode == 0:
            # No violations found
            return []

        violations = json.loads(result.stdout)
        # Convert both paths to absolute for comparison
        abs_file_path = str(file_path.resolve())
        return [v for v in violations if v["filename"] == abs_file_path]
    except Exception as e:
        print(f"Error getting violations for {file_path}: {e}")
        return []


def fix_violation_in_content(content: str, violation: dict[str, Any]) -> str:
    """Fix a specific TRY003 violation in content."""
    lines = content.split("\n")

    # Get violation details
    start_line = int(violation["location"]["row"]) - 1  # Convert to 0-based index
    end_line = int(violation["end_location"]["row"]) - 1  # Convert to 0-based index

    # Find the raise statement
    raise_line_idx = None
    for i in range(start_line, min(end_line + 1, len(lines))):
        if "raise" in lines[i]:
            raise_line_idx = i
            break

    if raise_line_idx is None:
        return content

    # Get the raise line
    raise_line = lines[raise_line_idx]

    # Extract indentation
    indent_match = re.match(r"^(\s*)", raise_line)
    indent = indent_match.group(1) if indent_match else ""

    # Check if this is a single-line or multi-line raise
    if raise_line.strip().endswith(")"):
        # Single line raise
        match = re.match(r"^(\s*)raise\s+(\w+)\(([^)]+)\)\s*$", raise_line)
        if match:
            _, exception_type, error_content = match.groups()

            # Create error message variable and new raise
            error_var_line = f"{indent}error_message = {error_content}"
            new_raise_line = f"{indent}raise {exception_type}(error_message)"

            # Replace the raise line with the two new lines
            lines[raise_line_idx] = error_var_line
            lines.insert(raise_line_idx + 1, new_raise_line)
    else:
        # Multi-line raise - collect all lines until closing paren
        raise_lines = []
        paren_count = 0
        i = raise_line_idx

        while i < len(lines):
            line = lines[i]
            raise_lines.append(line)
            paren_count += line.count("(") - line.count(")")
            i += 1

            if paren_count == 0:
                break

        # Extract error content from the multi-line raise
        full_raise = "\n".join(raise_lines)
        start_paren = full_raise.find("(")
        end_paren = full_raise.rfind(")")

        if start_paren != -1 and end_paren != -1:
            error_content = full_raise[start_paren + 1 : end_paren].strip()

            # Extract exception type
            exception_match = re.match(r"^(\s*)raise\s+(\w+)\(", raise_lines[0])
            if exception_match:
                _, exception_type = exception_match.groups()

                # Create error message variable and new raise
                # For multi-line error content, we need to preserve the formatting
                # The error_content should be properly formatted with line breaks
                if "\n" in error_content:
                    # Multi-line error content - wrap in parentheses
                    error_var_line = (
                        f"{indent}error_message = (\n{error_content}\n{indent})"
                    )
                else:
                    # Single line error content
                    error_var_line = f"{indent}error_message = {error_content}"
                new_raise_line = f"{indent}raise {exception_type}(error_message)"

                # Replace the multi-line raise with the two new lines
                # Remove the old lines (in reverse order to maintain indices)
                for j in range(len(raise_lines) - 1, -1, -1):
                    del lines[raise_line_idx + j]

                # Insert the new lines
                lines.insert(raise_line_idx, error_var_line)
                lines.insert(raise_line_idx + 1, new_raise_line)

    return "\n".join(lines)


def process_file(file_path: Path, *, dry_run: bool = False) -> bool:
    """Process a single file to fix TRY003 violations."""
    try:
        # Get violations for this file
        violations = get_try003_violations(file_path)

        if not violations:
            return False

        if dry_run:
            print(f"Would fix {len(violations)} TRY003 violations in {file_path}")
            for v in violations:
                line_num = int(v["location"]["row"])
                print(f"  Line {line_num}: {v['message']}")
            return True

        # Read file content
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Fix each violation (process in reverse order to maintain line numbers)
        for violation in reversed(violations):
            content = fix_violation_in_content(content, violation)

        # Write back the fixed content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Fixed {len(violations)} TRY003 violations in {file_path}")
        return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main() -> None:
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Fix TRY003 violations")
    parser.add_argument("files", nargs="*", help="Files to process")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be changed"
    )
    parser.add_argument("--test", action="store_true", help="Test on a small subset")

    args = parser.parse_args()

    if args.test:
        test_files = [
            "/workspaces/data-fetcher-sftp/src/data_fetcher_core/fetcher.py",
            "/workspaces/data-fetcher-sftp/src/data_fetcher_core/queue/kv_store_queue.py",
        ]
        print("Testing on a small subset of files first...")
        for test_file_path in test_files:
            if Path(test_file_path).exists():
                process_file(Path(test_file_path), dry_run=args.dry_run)
        return

    violation_files: list[Path]
    if args.files:
        violation_files = [Path(f) for f in args.files if Path(f).exists()]
    else:
        # Get all files with TRY003 violations
        result = subprocess.run(
            [
                "/usr/local/python/current/bin/poetry",
                "run",
                "ruff",
                "check",
                "--select",
                "TRY003",
                "--output-format=json",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd="/workspaces/data-fetcher-sftp",
        )

        if result.returncode == 0:
            # No violations found
            violations = []
        elif result.returncode == 1:
            # Violations found
            violations = json.loads(result.stdout)
        else:
            print("Error running ruff check")
            return

        violation_files = [Path(v["filename"]) for v in violations]

    print(f"Processing {len(violation_files)} files...")

    total_fixed = 0
    for file_path in violation_files:
        if process_file(file_path, dry_run=args.dry_run):
            total_fixed += 1

    print(f"Processed {total_fixed} files with changes")


if __name__ == "__main__":
    main()
