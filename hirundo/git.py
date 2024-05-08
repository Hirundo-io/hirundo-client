from pydantic import BaseModel
import pydantic
from pydantic_core import Url


class GitPlainAuthBase(BaseModel):
    username: str
    password: str


class GitSSHAuthBase(BaseModel):
    ssh_key: str
    ssh_password: str | None


class GitRepo(BaseModel):
    name: str
    repository_url: Url
    owner_id: int | None = None

    plain_auth: GitPlainAuthBase | None = pydantic.Field(
        examples=[None, {"username": "ben", "password": "password"}]
    )
    ssh_auth: GitSSHAuthBase | None = pydantic.Field(
        examples=[
            {
                "ssh_key": "SOME_PRIVATE_SSH_KEY",
                "ssh_password": "SOME_SSH_KEY_PASSWORD",
            },
            None,
        ]
    )
