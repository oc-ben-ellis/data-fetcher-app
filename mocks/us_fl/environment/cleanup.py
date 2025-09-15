import subprocess
from pathlib import Path


def main() -> None:
    # Reset SFTP server state by re-running setup script or clearing data directory
    env_dir = Path(__file__).parent
    setup_script = env_dir / "setup-mock-data.sh"
    if setup_script.exists():
        subprocess.run(["bash", str(setup_script)], check=True, cwd=str(env_dir))


if __name__ == "__main__":
    main()
