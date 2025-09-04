"""Documentation building and generation script.

This module provides the build_docs script for converting markdown documentation
to HTML, including navigation, styling, and cross-referencing.
"""

import re
import shutil
from pathlib import Path
from typing import Any

import markdown
from jinja2 import Environment, Template
from pygments.formatters import HtmlFormatter

#!/usr/bin/env python3
"""
Documentation builder for OC Fetcher.
Converts README.md and docs/*.md files to HTML with modern styling.
"""

try:
    from cairosvg import svg2png  # type: ignore[import-untyped]

    CAIRO_AVAILABLE = True
except ImportError:
    CAIRO_AVAILABLE = False


class DocBuilder:
    """Builder for generating HTML documentation from markdown files."""

    def __init__(
        self, source_dir: str = ".", output_dir: str = "docs/rendered"
    ) -> None:
        """Initialize the documentation builder.

        Args:
            source_dir: Source directory containing markdown files.
            output_dir: Output directory for generated HTML.
        """
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.md = markdown.Markdown(
            extensions=[
                "markdown.extensions.codehilite",
                "markdown.extensions.fenced_code",
                "markdown.extensions.tables",
                "markdown.extensions.toc",
                "markdown.extensions.attr_list",
                "markdown.extensions.def_list",
                "markdown.extensions.footnotes",
            ],
            extension_configs={
                "codehilite": {
                    "css_class": "highlight",
                    "use_pygments": True,
                    "noclasses": True,
                }
            },
        )

        # Create Jinja2 environment - using inline templates, so no FileSystemLoader needed
        self.jinja_env = Environment(autoescape=True)

        # Navigation structure
        self.nav_items: list[dict[str, Any]] = []
        self.current_page: str | None = None

    def setup_directories(self) -> None:
        """Create output directories and copy assets."""
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create assets directory
        assets_dir = self.output_dir / "assets"
        assets_dir.mkdir(exist_ok=True)

        # Copy any existing assets from docs/diagrams
        diagrams_dir = self.source_dir / "docs" / "diagrams"
        if diagrams_dir.exists():
            for file_path in diagrams_dir.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(diagrams_dir)
                    dest_path = assets_dir / relative_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, dest_path)

        # Copy assets from docs/assets
        assets_source_dir = self.source_dir / "docs" / "assets"
        if assets_source_dir.exists():
            for file_path in assets_source_dir.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(assets_source_dir)
                    dest_path = assets_dir / relative_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, dest_path)

    def convert_svg_to_png(
        self, svg_path: Path, png_path: Path, dpi: int = 300
    ) -> bool:
        """Convert SVG file to PNG."""
        if not CAIRO_AVAILABLE:
            print(f"Warning: CairoSVG not available, skipping conversion of {svg_path}")
            return False

        try:
            with open(svg_path, "rb") as svg_file:
                svg2png(
                    file_obj=svg_file,
                    write_to=str(png_path),
                    dpi=dpi,
                    background_color="transparent",
                )
            print(f"✓ Converted {svg_path} to {png_path}")
            return True
        except Exception as e:
            print(f"Error converting {svg_path} to PNG: {e}")
            return False

    def process_svg_assets(self) -> None:
        """Process SVG assets and convert them to PNG for documentation."""
        assets_dir = self.output_dir / "assets"

        # Find all SVG files in the assets directory
        for svg_file in assets_dir.rglob("*.svg"):
            # Create PNG path with same name
            png_file = svg_file.with_suffix(".png")

            # Convert SVG to PNG
            if self.convert_svg_to_png(svg_file, png_file):
                print(f"Generated PNG: {png_file}")
            else:
                print(f"Failed to convert: {svg_file}")

    def get_markdown_files(self) -> list[Path]:
        """Get all markdown files to process."""
        files: list[Path] = []

        # Add README.md
        readme_path = self.source_dir / "README.md"
        if readme_path.exists():
            files.append(readme_path)

        # Add docs/*.md files (excluding subdirectories for now)
        docs_dir = self.source_dir / "docs"
        if docs_dir.exists():
            for md_file in docs_dir.glob("*.md"):
                if md_file.name != "README.md":  # Avoid duplicate
                    # Exclude architecture_diagram.md from documentation generation
                    if md_file.name != "architecture_diagram.md":
                        files.append(md_file)

        # Add docs/*/*.md files (subdirectories)
        if docs_dir.exists():
            for md_file in docs_dir.rglob("*.md"):
                if md_file.parent != docs_dir:  # Only subdirectory files
                    if md_file.name != "README.md":  # Avoid duplicate
                        files.append(md_file)

        return sorted(files)

    def extract_title(self, content: str) -> str:
        """Extract title from markdown content."""
        lines = content.split("\n")
        for line in lines:
            if line.startswith("# "):
                return line[2:].strip()
        return "Documentation"

    def process_markdown_content(self, content: str, file_path: Path) -> str:
        """Process markdown content and convert to HTML."""
        # Filter out the "View Rendered Documentation" section for HTML generation
        if file_path.name == "README.md" and file_path.parent == self.source_dir:
            content = self.filter_rendered_docs_section(content)

        # Convert markdown to HTML
        html_content = self.md.convert(content)

        # Fix internal links
        html_content = self.fix_internal_links(html_content, file_path)

        return html_content

    def filter_rendered_docs_section(self, content: str) -> str:
        """Filter out the 'View Rendered Documentation' section from README.md."""
        lines = content.split("\n")
        filtered_lines: list[str] = []
        skip_section = False

        for line in lines:
            # Check if this is the start of the section we want to skip
            if line.strip() == "## 📖 View Rendered Documentation":
                skip_section = True
                continue

            # Check if we've reached the next section (## Key Features)
            if skip_section and line.strip() == "## Key Features":
                skip_section = False

            # Add the line if we're not skipping
            if not skip_section:
                filtered_lines.append(line)

        return "\n".join(filtered_lines)

    def fix_internal_links(self, html_content: str, file_path: Path) -> str:
        """Fix internal markdown links and image paths to point to correct locations."""
        # Pattern to match markdown links
        link_pattern = r'href="([^"]*\.md)"'

        def replace_link(match: re.Match[str]) -> str:
            link = match.group(1)
            if link.startswith("http"):
                return match.group(0)  # Keep external links as-is

            # Convert .md to .html
            if link.endswith(".md"):
                link = link[:-3] + ".html"

            # Handle relative paths
            if not link.startswith("/"):
                # If we're in a subdirectory, adjust the path
                if file_path.parent.name == "docs":
                    link = "../" + link

            return f'href="{link}"'

        # Fix markdown links
        html_content = re.sub(link_pattern, replace_link, html_content)

        # Pattern to match image src paths
        img_pattern = r'src="([^"]*)"'

        def replace_img(match: re.Match[str]) -> str:
            src = match.group(1)
            if src.startswith("http"):
                return match.group(0)  # Keep external images as-is

            # Fix docs/assets/ paths to assets/
            if src.startswith("docs/assets/"):
                src = src.replace("docs/assets/", "assets/")

            # Fix diagrams/png/ and diagrams/svg/ paths to assets/png/ and assets/svg/
            if src.startswith("diagrams/png/"):
                src = src.replace("diagrams/png/", "assets/png/")
            elif src.startswith("diagrams/svg/"):
                src = src.replace("diagrams/svg/", "assets/svg/")

            # Handle subdirectory pages - need to go up one level for assets
            # But don't add ../ for the root README.md
            if file_path.parent != self.source_dir / "docs" and not (
                file_path.name == "README.md" and file_path.parent == self.source_dir
            ):
                if src.startswith("assets/"):
                    src = "../" + src
                elif src.startswith("../diagrams/"):
                    src = src.replace("../diagrams/", "../assets/")

            # Convert SVG references to PNG for better compatibility
            if src.endswith(".svg"):
                png_src = src.replace(".svg", ".png")
                return f'src="{png_src}"'

            return f'src="{src}"'

        # Fix image paths
        html_content = re.sub(img_pattern, replace_img, html_content)

        return html_content

    def create_navigation(self, files: list[Path]) -> list[dict[str, Any]]:
        """Create navigation structure."""
        nav_items: list[dict[str, Any]] = []

        # Define the order for root-level documents
        root_doc_order = ["overview.md", "documentation_guide.md", "troubleshooting.md"]

        # Group files by directory
        file_groups: dict[str, list[Path]] = {}
        root_files: list[Path] = []

        for file_path in files:
            if file_path.name == "README.md" and file_path.parent == self.source_dir:
                # Main README
                content = file_path.read_text(encoding="utf-8")
                title = self.extract_title(content)
                nav_items.insert(
                    0,
                    {
                        "title": "Home",
                        "url": "index.html",
                        "file_path": file_path,
                        "is_home": True,
                        "section": None,
                    },
                )
            elif (
                file_path.parent == self.source_dir / "docs"
                and file_path.name in root_doc_order
            ):
                # Root-level docs files - add to special list for ordering
                root_files.append(file_path)
            else:
                # Group by section (directory)
                section = (
                    file_path.parent.name
                    if file_path.parent != self.source_dir / "docs"
                    else "main"
                )
                if section not in file_groups:
                    file_groups[section] = []
                file_groups[section].append(file_path)

        # Process root-level docs in the defined order
        for filename in root_doc_order:
            for file_path in root_files:
                if file_path.name == filename:
                    content = file_path.read_text(encoding="utf-8")
                    title = self.extract_title(content)
                    url = f"{file_path.stem}.html"
                    nav_items.append(
                        {
                            "title": title,
                            "url": url,
                            "file_path": file_path,
                            "is_home": False,
                            "section": None,
                        }
                    )
                    break

        # Process each section - sort by numbered prefixes
        section_items: list[tuple[str, list[Path]]] = []
        for section, section_files in file_groups.items():
            if section == "main":
                # Main docs files (any remaining ones not in root_doc_order)
                for file_path in section_files:
                    if file_path.name not in root_doc_order:
                        content = file_path.read_text(encoding="utf-8")
                        title = self.extract_title(content)
                        url = f"{file_path.stem}.html"
                        nav_items.append(
                            {
                                "title": title,
                                "url": url,
                                "file_path": file_path,
                                "is_home": False,
                                "section": None,
                            }
                        )
            else:
                # Subdirectory files - collect for sorting
                section_items.append((section, section_files))

        # Sort sections by their numbered prefixes
        def sort_key(section_tuple: tuple[str, list[Path]]) -> int:
            section_name = section_tuple[0]
            # Extract number from prefix (e.g., "01_architecture" -> 1)
            if "_" in section_name:
                try:
                    prefix = section_name.split("_")[0]
                    return int(prefix)
                except ValueError:
                    return 999  # Put non-numbered sections at the end
            return 999

        section_items.sort(key=sort_key)

        # Process sorted sections
        for section, section_files in section_items:
            # Clean section name for display (remove numbered prefix)
            if "_" in section:
                section_title = section.split("_", 1)[1].replace("_", " ").title()
            else:
                section_title = section.replace("_", " ").title()

            nav_items.append(
                {
                    "title": section_title,
                    "url": None,
                    "file_path": None,
                    "is_home": False,
                    "section": section,
                    "is_section_header": True,
                }
            )

            # Check if there's a README.md in this section
            section_readme = self.source_dir / "docs" / section / "README.md"
            ordered_files: list[Path] = []

            if section_readme.exists():
                # Parse README.md to get ordered file list
                readme_content = section_readme.read_text(encoding="utf-8")
                ordered_files = self.parse_readme_ordering(
                    readme_content, section_files
                )
            else:
                # Fall back to alphabetical ordering
                ordered_files = sorted(section_files, key=lambda x: x.name)

            for file_path in ordered_files:
                content = file_path.read_text(encoding="utf-8")
                title = self.extract_title(content)
                url = f"{section}/{file_path.stem}.html"
                nav_items.append(
                    {
                        "title": title,
                        "url": url,
                        "file_path": file_path,
                        "is_home": False,
                        "section": section,
                        "is_section_header": False,
                    }
                )

        return nav_items

    def parse_readme_ordering(
        self, readme_content: str, section_files: list[Path]
    ) -> list[Path]:
        """Parse README.md content to determine file ordering."""
        ordered_files: list[Path] = []
        file_dict = {f.name: f for f in section_files}

        # Look for numbered list items that reference markdown files
        lines = readme_content.split("\n")
        for line in lines:
            # Match patterns like "1. **[filename.md](filename.md)** - description"
            # or "1. filename.md - description"
            match = re.search(
                r"^\d+\.\s*\*\*?\[?([^\]]*\.md)\]?\([^)]*\)?\*\*?\s*[-–]\s*(.*)", line
            )
            if not match:
                # Try simpler pattern without markdown formatting
                match = re.search(r"^\d+\.\s*([^\s]*\.md)\s*[-–]\s*(.*)", line)

            if match:
                filename = match.group(1)
                if filename in file_dict:
                    ordered_files.append(file_dict[filename])

        # Add any remaining files that weren't in the README
        for file_path in section_files:
            if file_path not in ordered_files:
                ordered_files.append(file_path)

        return ordered_files

    def create_html_template(self) -> Template:
        """Create the HTML template."""
        template_content = """

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Fetcher Documentation</title>
    <link rel="stylesheet" href="{{ asset_prefix }}assets/style.css">
    <link rel="stylesheet" href="{{ asset_prefix }}assets/pygments.css">
    <link rel="icon" type="image/x-icon" href="{{ asset_prefix }}assets/favicon.ico">
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="header-content">
                <h1 class="logo">
                    <img src="{{ asset_prefix }}assets/DATA_FETCHER_Logo_New.png" alt="OC Fetcher Logo" class="logo-img">
                </h1>
            </div>
        </header>

        <div class="main-content">
            <nav class="sidebar">
                <ul class="nav-list">
                    {% for item in nav_items %}
                    {% if item.is_section_header %}
                    <li class="nav-section">
                        <button class="nav-section-toggle" onclick="toggleSection(this)">
                            <span class="toggle-icon">▼</span>
                            <span class="section-title">{{ item.title }}</span>
                        </button>
                        <ul class="nav-subsection">
                    {% elif item.section and not item.is_section_header %}
                    <li class="nav-item {% if item.url == current_page %}active{% endif %}">
                        <a href="{{ item.url }}" class="nav-link nav-subitem">
                            {{ item.title }}
                        </a>
                    </li>
                    {% if loop.index < nav_items|length and nav_items[loop.index].is_section_header %}
                        </ul>
                    </li>
                    {% elif loop.index == nav_items|length %}
                        </ul>
                    </li>
                    {% endif %}
                    {% else %}
                    <li class="nav-item {% if item.url == current_page %}active{% endif %}">
                        <a href="{{ item.url }}" class="nav-link">
                            {% if item.is_home %}🏠{% endif %}
                            {{ item.title }}
                        </a>
                    </li>
                    {% endif %}
                    {% endfor %}
                </ul>
            </nav>

            <main class="content">
                <article class="documentation">
                    {{ content | safe }}
                </article>
            </main>
        </div>

        <footer class="footer">
            <p>&copy; 2024 OpenCorporates. Built with OC Fetcher.</p>
        </footer>
    </div>

    <script>
        function toggleSection(button) {
            const section = button.parentElement;
            const subsection = section.querySelector('.nav-subsection');
            const icon = button.querySelector('.toggle-icon');
            const sectionTitle = button.querySelector('.section-title').textContent;

            if (subsection.style.display === 'none') {
                subsection.style.display = 'block';
                icon.textContent = '▼';
                section.classList.remove('collapsed');
                // Save expanded state
                localStorage.setItem(`nav_section_${sectionTitle}`, 'expanded');
            } else {
                subsection.style.display = 'none';
                icon.textContent = '▶';
                section.classList.add('collapsed');
                // Save collapsed state
                localStorage.setItem(`nav_section_${sectionTitle}`, 'collapsed');
            }
        }

        // Initialize sections with persistent state
        document.addEventListener('DOMContentLoaded', function() {
            const currentPage = '{{ current_page }}';
            const sections = document.querySelectorAll('.nav-section');

            sections.forEach(section => {
                const subsection = section.querySelector('.nav-subsection');
                const toggle = section.querySelector('.nav-section-toggle');
                const icon = toggle.querySelector('.toggle-icon');
                const sectionTitle = toggle.querySelector('.section-title').textContent;

                // Check if this section contains the current page
                const hasCurrentPage = subsection.querySelector(`a[href="${currentPage}"]`);

                // Get saved state from localStorage
                const savedState = localStorage.getItem(`nav_section_${sectionTitle}`);

                if (hasCurrentPage) {
                    // Always expand the section containing the current page
                    subsection.style.display = 'block';
                    icon.textContent = '▼';
                    section.classList.remove('collapsed');
                    localStorage.setItem(`nav_section_${sectionTitle}`, 'expanded');
                } else if (savedState === 'expanded') {
                    // Restore expanded state
                    subsection.style.display = 'block';
                    icon.textContent = '▼';
                    section.classList.remove('collapsed');
                } else {
                    // Default to collapsed state
                    subsection.style.display = 'none';
                    icon.textContent = '▶';
                    section.classList.add('collapsed');
                    localStorage.setItem(`nav_section_${sectionTitle}`, 'collapsed');
                }
            });
        });
    </script>
</body>
</html>
"""
        return Template(template_content)

    def create_css(self) -> None:
        """Create modern CSS styling."""
        css_content = """
/* Reset and base styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: white;
}

.container {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

/* Header */
.header {
    background: white;
    color: rgb(159, 31, 52);
    padding: 0.75rem 0;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.header-content {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 2rem;
}

.logo {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    font-size: 1.8rem;
    font-weight: 700;
    color: rgb(159, 31, 52);
}

.logo-img {
    height: 48px;
    width: auto;
}

/* Hide border-bottom for header h1 */
.header h1 {
    border-bottom: none;
    padding-bottom: 0;
}

/* Main content */
.main-content {
    flex: 1;
    display: flex;
    max-width: 1200px;
    margin: 0 auto;
    background: white;
}

/* Sidebar */
.sidebar {
    width: 280px;
    background: white;
    border-right: 1px solid #e9ecef;
    padding: 0;
    position: sticky;
    top: 0;
    height: calc(100vh - 80px);
    overflow-y: auto;
}

.nav-list {
    list-style: none;
}

.nav-item {
    margin: 0;
}

.nav-link {
    display: block;
    padding: 0.75rem 2rem;
    color: #495057;
    text-decoration: none;
    transition: all 0.2s ease;
    border-left: 3px solid transparent;
}

.nav-link:hover {
    background: #fef2f2;
    color: rgb(159, 31, 52);
    border-left-color: rgb(159, 31, 52);
}

.nav-item.active .nav-link {
    background: #fef2f2;
    color: rgb(159, 31, 52);
    border-left-color: rgb(159, 31, 52);
    font-weight: 500;
}

/* Section headers */
.nav-section {
    margin: 1rem 0;
}

.nav-section-toggle {
    width: 100%;
    background: none;
    border: none;
    text-align: left;
    cursor: pointer;
    padding: 0.5rem 2rem;
    color: #6c757d;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
    border-bottom: 1px solid #e9ecef;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    transition: all 0.2s ease;
}

.nav-section-toggle:hover {
    background: #f8f9fa;
    color: #495057;
}

.toggle-icon {
    font-size: 0.7rem;
    transition: transform 0.2s ease;
}

.section-title {
    flex: 1;
}

.nav-subsection {
    list-style: none;
    margin: 0;
    padding: 0;
}

.nav-subitem {
    padding: 0.5rem 2rem 0.5rem 3rem !important;
    font-size: 0.9rem;
}

/* Content */
.content {
    flex: 1;
    padding: 1rem 2rem;
    overflow-y: auto;
}

.documentation {
    max-width: 800px;
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
    margin: 0.5rem 0;
    color: #2c3e50;
    font-weight: 600;
}

h1 {
    font-size: 2.5rem;
    border-bottom: 3px solid rgb(159, 31, 52);
    padding-bottom: 0.5rem;
}

h2 {
    font-size: 2rem;
    border-bottom: 2px solid #e9ecef;
    padding-bottom: 0.5rem;
}

h3 {
    font-size: 1.5rem;
}

h4 {
    font-size: 1.25rem;
}

p {
    margin: 1rem 0;
    line-height: 1.7;
}

/* Code blocks */
pre {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 6px;
    padding: 1rem;
    overflow-x: auto;
    margin: 1rem 0;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.9rem;
    line-height: 1.4;
}

code {
    background: #f1f3f4;
    padding: 0.2rem 0.4rem;
    border-radius: 3px;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.9em;
}

pre code {
    background: none;
    padding: 0;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
    background: white;
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

th, td {
    padding: 0.75rem;
    text-align: left;
    border-bottom: 1px solid #e9ecef;
}

th {
    background: #f8f9fa;
    font-weight: 600;
    color: #495057;
}

tr:hover {
    background: #f8f9fa;
}

/* Lists */
ul, ol {
    margin: 1rem 0;
    padding-left: 2rem;
}

li {
    margin: 0.5rem 0;
}

/* Links */
a {
    color: rgb(159, 31, 52);
    text-decoration: none;
    transition: color 0.2s ease;
}

a:hover {
    color: rgb(127, 25, 42);
    text-decoration: underline;
}

/* Blockquotes */
blockquote {
    border-left: 4px solid rgb(159, 31, 52);
    padding-left: 1rem;
    margin: 1rem 0;
    color: #6c757d;
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 0 6px 6px 0;
}

/* Images */
img {
    max-width: 100%;
    height: auto;
}

/* Logo images should keep their styling */
.logo-img {
}

/* Footer */
.footer {
    background: #343a40;
    color: white;
    text-align: center;
    padding: 2rem;
    margin-top: auto;
}

/* Responsive design */
@media (max-width: 768px) {
    .main-content {
        flex-direction: column;
    }

    .sidebar {
        width: 100%;
        height: auto;
        position: static;
    }

    .content {
        padding: 1rem;
    }

    h1 {
        font-size: 2rem;
    }

    h2 {
        font-size: 1.5rem;
    }
}

/* Syntax highlighting */
.highlight {
    background: #f8f9fa;
    border-radius: 6px;
    overflow: hidden;
}

.highlight pre {
    margin: 0;
    border: none;
    background: none;
}

/* Custom scrollbar */
.sidebar::-webkit-scrollbar {
    width: 6px;
}

.sidebar::-webkit-scrollbar-track {
    background: #f1f1f1;
}

.sidebar::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 3px;
}

.sidebar::-webkit-scrollbar-thumb:hover {
    background: #a8a8a8;
}
"""

        css_file = self.output_dir / "assets" / "style.css"
        css_file.write_text(css_content, encoding="utf-8")

    def create_pygments_css(self) -> None:
        """Create Pygments CSS for syntax highlighting."""
        formatter = HtmlFormatter(style="monokai")
        css_content = formatter.get_style_defs(".highlight")

        css_file = self.output_dir / "assets" / "pygments.css"
        css_file.write_text(css_content, encoding="utf-8")

    def build(self) -> None:
        """Build the documentation."""
        print("Building documentation...")

        # Setup directories
        self.setup_directories()

        # Process SVG assets and convert to PNG
        print("Processing SVG assets...")
        self.process_svg_assets()

        # Get markdown files
        files = self.get_markdown_files()
        if not files:
            print("No markdown files found!")
            return

        # Create navigation
        self.nav_items = self.create_navigation(files)

        # Create CSS files
        self.create_css()
        self.create_pygments_css()

        # Create HTML template
        template = self.create_html_template()

        # Process each file
        for file_path in files:
            print(f"Processing {file_path}...")

            # Read content
            content = file_path.read_text(encoding="utf-8")

            # Extract title
            title = self.extract_title(content)

            # Process content
            html_content = self.process_markdown_content(content, file_path)

            # Determine output filename and current page
            if file_path.name == "README.md" and file_path.parent == self.source_dir:
                output_file = self.output_dir / "index.html"
                current_page = "index.html"
            else:
                # Handle subdirectories
                if file_path.parent != self.source_dir / "docs":
                    # Subdirectory file
                    section_dir = self.output_dir / file_path.parent.name
                    section_dir.mkdir(exist_ok=True)
                    output_file = section_dir / f"{file_path.stem}.html"
                    current_page = f"{file_path.parent.name}/{file_path.stem}.html"
                else:
                    # Main docs file
                    output_file = self.output_dir / f"{file_path.stem}.html"
                    current_page = f"{file_path.stem}.html"

            # Determine asset path prefix based on file location
            # Only subdirectory files need the ../ prefix
            if (
                file_path.parent != self.source_dir / "docs"
                and file_path.parent != self.source_dir
            ):
                # Subdirectory file - need to go up one level for assets
                asset_prefix = "../"
            else:
                # Main docs file or README - assets are at same level
                asset_prefix = ""

            # Adjust navigation links for subdirectory pages
            adjusted_nav_items: list[dict[str, Any]] = []
            for item in self.nav_items:
                # Create a copy of the item to avoid modifying the original
                item_copy = item.copy()
                if item_copy.get("url"):
                    # Only adjust links for actual subdirectory files (not main docs files)
                    if (
                        file_path.parent != self.source_dir / "docs"
                        and file_path.parent != self.source_dir
                        and item_copy["url"]
                        and not item_copy["url"].startswith("http")
                    ):
                        # Subdirectory page - adjust navigation links
                        if item_copy["url"] == "index.html":
                            item_copy["url"] = "../index.html"
                        elif not item_copy["url"].startswith("../") and not item_copy[
                            "url"
                        ].startswith("http"):
                            item_copy["url"] = "../" + item_copy["url"]
                adjusted_nav_items.append(item_copy)

            # Render template
            html_output = template.render(
                title=title,
                content=html_content,
                nav_items=adjusted_nav_items,
                current_page=current_page,
                asset_prefix=asset_prefix,
            )

            # Write file
            output_file.write_text(html_output, encoding="utf-8")

        print(f"Documentation built successfully in {self.output_dir}")
        print(
            f"Open {self.output_dir}/index.html in your browser to view the documentation."
        )
        print("Or open docs/index.html to be redirected to the correct location.")


def main() -> None:
    """Main entry point."""
    builder = DocBuilder()
    builder.build()


if __name__ == "__main__":
    main()
