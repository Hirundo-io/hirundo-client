import re
from typing import Annotated
import typer

from hirundo.env import API_HOST


app = typer.Typer(name="hirundo", no_args_is_help=True)

def replace_env(env_name: str, env_value: str):
    dotenv = "./.env"
    regex = re.compile(rf"^{env_name}=.*$")
    with open(dotenv, "r") as f:
        lines = f.readlines()

    with open(dotenv, "w") as f:
        f.writelines(line for line in lines if not regex.search(line) and line != "\n")

    with open(dotenv, "a") as f:
        f.writelines(f"\n{env_name}={env_value}")


@app.command("setup")
def setup_api_key(api_key: Annotated[str, typer.Option(prompt="Please enter the API key value", help=f"Visit {API_HOST}/api-key to generate your API key.")]):
    """
    Setup the API key for the Hirundo client library.
    Values are saved to a .env file in the current directory for use by the library in requests.
    """
    replace_env("API_KEY", api_key)
    print("API key saved to .env for future use. Please do not share this file")

@app.command("change-remote")
def change_api_remote(
    api_host: Annotated[
        str,  # TODO: Change to HttpUrl when https://github.com/tiangolo/typer/pull/723 is merged
        typer.Option(
            prompt="Please enter the API server address",
            help=f"Current API server address: {API_HOST}. This should only be changed for on-premises usage",
        ),
    ],
):
    """
    Change the API server address for the Hirundo client library.
    This should only be used for on-premises usage.
    """
    replace_env("API_HOST", api_host)
    print("API host saved to .env for future use. Please do not share this file")

if __name__ == "__main__":
    app()
