import shutil
import subprocess
from pathlib import Path


def _docker_compose_cmd() -> list[str]:
    if shutil.which("docker"):
        return ["docker", "compose"]
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    raise RuntimeError("docker or docker-compose is required")


def _get_sftp_container_id(env_dir: Path) -> str:
    base = _docker_compose_cmd()
    proc = subprocess.run(
        [*base, "ps", "-q", "sftp-server"],
        check=True,
        cwd=str(env_dir),
        text=True,
        capture_output=True,
        timeout=60,
    )
    cid = (proc.stdout or "").strip()
    if not cid:
        raise RuntimeError("sftp-server container not running")
    return cid


def main() -> None:
    # Reset SFTP server state by clearing the data directory via docker exec
    env_dir = Path(__file__).parent
    container_id = _get_sftp_container_id(env_dir)
    subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            container_id,
            "sh",
            "-lc",
            "rm -rf /home/test/data/* && mkdir -p /home/test/data/doc/cor /home/test/data/doc/Quarterly/Cor",
        ],
        check=True,
        text=True,
        capture_output=True,
        timeout=60,
    )


if __name__ == "__main__":
    main()
