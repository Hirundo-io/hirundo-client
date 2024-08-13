import re
import sys
from typing import Annotated
from urllib.parse import urlparse

import typer

from hirundo._env import API_HOST

docs = "sphinx" in sys.modules
hirundo_epilog = (
    None
    if docs
    else "Made with ❤️ by Hirundo. Visit https://www.hirundo.io for more information."
)


app = typer.Typer(
    name="hirundo",
    no_args_is_help=True,
    rich_markup_mode="rich",
    epilog=hirundo_epilog,
)


def upsert_env(var_name: str, var_value: str):
    """
    Change an environment variable in the .env file.
    If the variable does not exist, it will be added.

    Args:
        var_name: The name of the environment variable to change.
        var_value: The new value of the environment variable.
    """
    dotenv = "./.env"
    regex = re.compile(rf"^{var_name}=.*$")
    with open(dotenv) as f:
        lines = f.readlines()

    with open(dotenv, "w") as f:
        f.writelines(line for line in lines if not regex.search(line) and line != "\n")

    with open(dotenv, "a") as f:
        f.writelines(f"\n{var_name}={var_value}")


def fix_api_host(api_host: str):
    if not api_host.startswith("http") and not api_host.startswith("https"):
        api_host = f"https://{api_host}"
        print(
            "API host must start with 'http://' or 'https://'. Automatically added 'https://'."
        )
    if (url := urlparse(api_host)) and url.path != "":
        print("API host should not contain a path. Removing path.")
        api_host = f"{url.scheme}://{url.hostname}"
    return api_host


@app.command("set-api-key", epilog=hirundo_epilog)
def setup_api_key(
    api_key: Annotated[
        str,
        typer.Option(
            prompt="Please enter the API key value",
            help=""
            if docs
            else f"Visit '{API_HOST}/api-key' to generate your API key.",
        ),
    ],
):
    """
    Setup the API key for the Hirundo client library.
    Values are saved to a .env file in the current directory for use by the library in requests.
    """
    upsert_env("API_KEY", api_key)
    print("API key saved to .env for future use. Please do not share the .env file")


@app.command("change-remote", epilog=hirundo_epilog)
def change_api_remote(
    api_host: Annotated[
        str,  # TODO: Change to HttpUrl when https://github.com/tiangolo/typer/pull/723 is merged
        typer.Option(
            prompt="Please enter the API server address",
            help=""
            if docs
            else f"Current API server address: '{API_HOST}'. This is the same address where you access the Hirundo web interface.",
        ),
    ],
):
    """
    Change the API server address for the Hirundo client library.
    This is the same address where you access the Hirundo web interface.
    """
    api_host = fix_api_host(api_host)

    upsert_env("API_HOST", api_host)
    print("API host saved to .env for future use. Please do not share this file")


@app.command("setup", epilog=hirundo_epilog)
def setup(
    api_key: Annotated[
        str,
        typer.Option(
            prompt="Please enter the API key value",
            help=""
            if docs
            else f"Visit '{API_HOST}/api-key' to generate your API key.",
        ),
    ],
    api_host: Annotated[
        str,  # TODO: Change to HttpUrl as above
        typer.Option(
            prompt="Please enter the API server address",
            help=""
            if docs
            else f"Current API server address: '{API_HOST}'. This is the same address where you access the Hirundo web interface.",
        ),
    ],
):
    """
    Setup the Hirundo client library.
    """
    api_host = fix_api_host(api_host)
    upsert_env("API_HOST", api_host)
    upsert_env("API_KEY", api_key)
    print(
        "API host and API key saved to .env for future use. Please do not share this file"
    )


typer_click_object = typer.main.get_command(app)

if __name__ == "__main__":
    app()
