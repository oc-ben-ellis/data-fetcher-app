from pathlib import Path


def main() -> None:
    # For HTTP mocks, bring environment back to a clean slate if any stateful service exists
    env_dir = Path(__file__).parent
    # No-op for now. If mock server stores state, clear it here.
    _ = env_dir


if __name__ == "__main__":
    main()
