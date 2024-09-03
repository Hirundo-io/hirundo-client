import enum
import os
from pathlib import Path

from dotenv import load_dotenv


class EnvLocation(enum.Enum):
    DOTENV = Path.cwd() / ".env"
    HOME = Path.home() / ".hirundo.conf"


if os.path.exists(EnvLocation.DOTENV.value):
    load_dotenv(EnvLocation.DOTENV.value)
elif os.path.exists(EnvLocation.HOME.value):
    load_dotenv(EnvLocation.HOME.value)
else:
    if not os.getenv("API_KEY") and not os.getenv("API_HOST"):
        raise ValueError(
            f"No {EnvLocation.HOME.value} or {EnvLocation.DOTENV.value} files found and API_KEY and API_HOST environment variables are not set"
        )

API_HOST = os.getenv("API_HOST", "https://api.hirundo.io")
API_KEY = os.getenv("API_KEY")


def check_api_key():
    if not API_KEY:
        raise ValueError(
            "API_KEY is not set. Please run `hirundo setup` to set the API key"
        )
