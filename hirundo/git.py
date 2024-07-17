import logging
import re
from typing import Annotated, Union
from pydantic import BaseModel, field_validator
import pydantic
from pydantic_core import Url
import requests

from hirundo.env import API_HOST
from hirundo.headers import auth_headers, json_headers


logger = logging.getLogger(__name__)


class GitPlainAuthBase(BaseModel):
    username: str
    password: str


class GitSSHAuthBase(BaseModel):
    ssh_key: str
    ssh_password: Union[str, None]


class GitRepo(BaseModel):
    id: Union[int, None] = None

    name: str
    repository_url: Annotated[str, Url]
    organization_id: Union[int, None] = None

    plain_auth: Union[GitPlainAuthBase, None] = pydantic.Field(
        default=None, examples=[None, {"username": "ben", "password": "password"}]
    )
    ssh_auth: Union[GitSSHAuthBase, None] = pydantic.Field(
        default=None,
        examples=[
            {
                "ssh_key": "SOME_PRIVATE_SSH_KEY",
                "ssh_password": "SOME_SSH_KEY_PASSWORD",
            },
            None,
        ],
    )

    @field_validator("repository_url", mode="before", check_fields=True)
    @classmethod
    def check_valid_repository_url(cls, repository_url: str):
        # Check if the URL already has a protocol
        if not re.match(r"^[a-z]+://", repository_url):
            # Check if the URL has the `@` and `:` pattern with a non-numeric section before the next slash
            match = re.match(r"([^@]+@[^:]+):([^0-9/][^/]*)/(.+)", repository_url)
            if match:
                user_host = match.group(1)
                path = match.group(2) + "/" + match.group(3)
                rewritten_url = f"ssh://{user_host}/{path}"
                logger.info("Modified Git repo to add SSH protocol", rewritten_url)
                return rewritten_url
        if not repository_url.startswith("ssh://") and not repository_url.startswith(
            "https://"
        ):
            raise ValueError("Repository URL must start with 'ssh://' or 'https://'")
        return repository_url

    def create(self):
        git_repo = requests.post(
            f"{API_HOST}/git-repo/",
            json=self.model_dump(),
            headers={
                **json_headers,
                **auth_headers,
            },
        )
        git_repo.raise_for_status()
        git_repo_id = git_repo.json()["id"]
        self.id = git_repo_id
        return git_repo_id

    @staticmethod
    def list():
        git_repos = requests.get(
            f"{API_HOST}/git-repo/",
            headers={
                **auth_headers,
            },
        )
        git_repos.raise_for_status()
        return git_repos.json()

    @staticmethod
    def delete_by_id(id: int):
        git_repo = requests.delete(
            f"{API_HOST}/git-repo/{id}",
            headers={
                **auth_headers,
            },
        )
        git_repo.raise_for_status()

    def delete(self):
        if not self.id:
            raise ValueError("No GitRepo has been created")
        GitRepo.delete_by_id(self.id)
