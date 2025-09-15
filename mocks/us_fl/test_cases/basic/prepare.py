import os
import subprocess
from pathlib import Path


def main() -> None:
    # For SFTP-based tests, ensure the mock data directory is reset by calling setup-mock-data.sh if present
    env_dir = Path(__file__).resolve().parents[2] / "environment"
    setup_script = env_dir / "setup-mock-data.sh"
    if setup_script.exists():
        subprocess.run(["bash", str(setup_script)], check=True, cwd=str(env_dir))

    _ = os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566")


if __name__ == "__main__":
    main()
