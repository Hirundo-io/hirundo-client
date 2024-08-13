import os

from dotenv import load_dotenv

load_dotenv()

API_HOST = os.getenv("API_HOST", "https://api.hirundo.io")
API_KEY = os.getenv("API_KEY")


def check_api_key():
    if not API_KEY:
        raise ValueError(
            "API_KEY is not set. Please run `hirundo setup` to set the API key"
        )
