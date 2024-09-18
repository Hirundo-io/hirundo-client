import re
import typing
from typing import Annotated

import pydantic
import requests
from pydantic import BaseModel, field_validator
from pydantic_core import Url

from hirundo._env import API_HOST
from hirundo._headers import get_auth_headers, json_headers
from hirundo._http import raise_for_status_with_reason
from hirundo._timeouts import MODIFY_TIMEOUT, READ_TIMEOUT
from hirundo.logger import get_logger

logger = get_logger(__name__)


class GitPlainAuthBase(BaseModel):
    username: str
    """
    The username for the Git repository
    """
    password: str
    """
    The password for the Git repository
    """


class GitSSHAuthBase(BaseModel):
    ssh_key: str
    """
    The SSH key for the Git repository
    """
    ssh_password: typing.Optional[str]
    """
    The password for the SSH key for the Git repository.
    """


class GitRepo(BaseModel):
    id: typing.Optional[int] = None
    """
    The ID of the Git repository.
    """

    name: str
    """
    A name to identify the Git repository in the Hirundo system.
    """
    repository_url: Annotated[str, Url]
    """
    The URL of the Git repository, it should start with `ssh://` or `https://` or be in the form `user@host:path`.
    If it is in the form `user@host:path`, it will be rewritten to `ssh://user@host:path`.
    """
    organization_id: typing.Optional[int] = None
    """
    The ID of the organization that the Git repository belongs to.
    If not provided, it will be assigned to your default organization.
    """

    plain_auth: typing.Optional[GitPlainAuthBase] = pydantic.Field(
        default=None, examples=[None, {"username": "ben", "password": "password"}]
    )
    """
    The plain authentication details for the Git repository.
    Use this if using a special user with a username and password for authentication.
    """
    ssh_auth: typing.Optional[GitSSHAuthBase] = pydantic.Field(
        default=None,
        examples=[
            {
                "ssh_key": "SOME_PRIVATE_SSH_KEY",
                "ssh_password": "SOME_SSH_KEY_PASSWORD",
            },
            None,
        ],
    )
    """
    The SSH authentication details for the Git repository.
    Use this if using an SSH key for authentication.
    Optionally, you can provide a password for the SSH key.
    """

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
        """
        Create a Git repository in the Hirundo system.
        """
        git_repo = requests.post(
            f"{API_HOST}/git-repo/",
            json=self.model_dump(),
            headers={
                **json_headers,
                **get_auth_headers(),
            },
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(git_repo)
        git_repo_id = git_repo.json()["id"]
        self.id = git_repo_id
        return git_repo_id

    @staticmethod
    def list():
        """
        List all Git repositories in the Hirundo system.
        """
        git_repos = requests.get(
            f"{API_HOST}/git-repo/",
            headers={
                **get_auth_headers(),
            },
            timeout=READ_TIMEOUT,
        )
        raise_for_status_with_reason(git_repos)
        return git_repos.json()

    @staticmethod
    def delete_by_id(git_repo_id: int):
        """
        Delete a Git repository by its ID.

        Args:
            git_repo_id: The ID of the Git repository to delete
        """
        git_repo = requests.delete(
            f"{API_HOST}/git-repo/{git_repo_id}",
            headers={
                **get_auth_headers(),
            },
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(git_repo)

    def delete(self):
        """
        Delete the Git repository created by this instance.
        """
        if not self.id:
            raise ValueError("No GitRepo has been created")
        GitRepo.delete_by_id(self.id)
