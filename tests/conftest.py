from pathlib import Path

from dotenv import load_dotenv


def pytest_configure() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)
