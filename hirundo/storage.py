import typing
from enum import Enum
from pathlib import Path

import pydantic
import requests
from pydantic import BaseModel, model_validator
from pydantic_core import Url

from hirundo._constraints import S3BucketUrl, StorageIntegrationName
from hirundo._env import API_HOST
from hirundo._headers import get_auth_headers, json_headers
from hirundo._http import raise_for_status_with_reason
from hirundo._timeouts import MODIFY_TIMEOUT, READ_TIMEOUT
from hirundo.git import GitRepo, GitRepoOut
from hirundo.logger import get_logger

logger = get_logger(__name__)


class StorageS3Base(BaseModel):
    endpoint_url: typing.Optional[Url] = None
    bucket_url: S3BucketUrl
    region_name: str
    # ⬆️ We could restrict this, but if we're allowing custom endpoints then the validation may be wrong
    access_key_id: typing.Optional[str] = None

    def get_url(self, path: typing.Union[str, Path]):
        return Url(
            f"s3://{self.bucket_url.removeprefix('s3://').removesuffix('/')}/{str(path).removeprefix('/')}"
        )


class StorageS3(StorageS3Base):
    secret_access_key: typing.Optional[str] = None


class StorageS3Out(StorageS3Base):
    pass


class StorageGCPBase(BaseModel):
    bucket_name: str
    project: str

    def get_url(self, path: typing.Union[str, Path]):
        return Url(f"gs://{self.bucket_name}/{str(path).removeprefix('/')}")


class StorageGCP(StorageGCPBase):
    credentials_json: typing.Optional[dict] = None


class StorageGCPOut(StorageGCPBase):
    pass


# TODO: Azure storage integration is coming soon
# class StorageAzure(BaseModel):
#     account_url: HttpUrl
#     container_name: str
#     tenant_id: str
#
#     def get_url(self, path: typing.Union[str, Path]):
#         return f"{str(self.account_url)}/{self.container_nam}/{path}"
# class StorageAzureOut(BaseModel):
#     container: str
#     account_url: str


def get_git_repo_url(repo_url: typing.Union[str, Url], path: typing.Union[str, Path]):
    if not isinstance(repo_url, Url):
        repo_url = Url(repo_url)
    return Url(
        f"{repo_url.scheme}{str(repo_url).removeprefix(repo_url.scheme)}{str(path).removeprefix('/')}"
    )


class StorageGit(BaseModel):
    repo_id: typing.Optional[int] = None
    """
    The ID of the Git repository in the Hirundo system.
    Either `repo_id` or `repo` must be provided.
    """
    repo: typing.Optional[GitRepo] = None
    """
    The Git repository to link to.
    Either `repo_id` or `repo` must be provided.
    """
    branch: str
    """
    The branch of the Git repository to link to.
    """

    @model_validator(mode="after")
    def validate_repo(self):
        if self.repo_id is None and self.repo is None:
            raise ValueError("Either repo_id or repo must be provided")
        return self

    def get_url(self, path: typing.Union[str, Path]):
        if not self.repo:
            raise ValueError("Repo must be provided to use `get_url`")
        repo_url = self.repo.repository_url
        return get_git_repo_url(repo_url, path)


class StorageGitOut(BaseModel):
    repo: GitRepoOut
    branch: str

    def get_url(self, path: typing.Union[str, Path]):
        repo_url = self.repo.repository_url
        return get_git_repo_url(repo_url, path)


class StorageTypes(str, Enum):
    """
    Enum for the different types of storage integrations.
    Supported types are:
    """

    S3 = "S3"
    GCP = "GCP"
    # AZURE = "Azure"  TODO: Azure storage integration is coming soon
    GIT = "Git"
    LOCAL = "Local"
    """
    Local storage integration is only supported for on-premises installations.
    """


class StorageIntegration(BaseModel):
    id: typing.Optional[int] = None
    """
    The ID of the `StorageIntegration` in the Hirundo system.
    """

    organization_id: typing.Optional[int] = None
    """
    The ID of the organization that the `StorageIntegration` belongs to.
    If not provided, it will be assigned to your default organization.
    """

    name: StorageIntegrationName
    """
    A name to identify the `StorageIntegration` in the Hirundo system.
    """
    type: typing.Optional[StorageTypes] = pydantic.Field(
        examples=[
            StorageTypes.S3,
            StorageTypes.GCP,
            # StorageTypes.AZURE,  TODO: Azure storage integration is coming soon
            StorageTypes.GIT,
        ]
    )
    """
    The type of the `StorageIntegration`.
    Supported types are:
    - `S3`
    - `GCP`
    - `Azure` (coming soon)
    - `Git`
    """
    s3: typing.Optional[StorageS3] = pydantic.Field(
        default=None,
        examples=[
            {
                "bucket_url": "s3://my-bucket",
                "region_name": "us-west-2",
                "access_key_id": "my-access-key",
                "secret_access_key": "REDACTED",
            },
            None,
            None,
            None,
        ],
    )
    """
    The Amazon Web Services (AWS) S3 storage integration details.
    Use this if you want to link to an S3 bucket.
    """
    gcp: typing.Optional[StorageGCP] = pydantic.Field(
        default=None,
        examples=[
            None,
            {
                "bucket_name": "my-bucket",
                "project": "my-project",
                "credentials_json": {
                    "type": "service_account",
                    "project_id": "my-project",
                    "private_key_id": "my-key-id",
                    "private_key": "REDACTED",
                    "client_email": "my-service-account@my-project.iam.gserviceaccount.com",
                    "client_id": "my-id",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/my-service-account%40my-project.iam.gserviceaccount.com",
                    "universe_domain": "googleapis.com",
                },
            },
            None,
            None,
        ],
    )
    """
    The Google Cloud (GCP) Storage integration details.
    Use this if you want to link to an GCS bucket.
    """
    azure: None = None
    # azure: typing.Optional[StorageAzure] = pydantic.Field(
    #     default=None,
    #     examples=[
    #         None,
    #         None,
    #         {
    #             "container": "my-container",
    #             "account_name": "my-account-name",
    #             "account_key": "my-account",
    #         },
    #         None,
    #     ],
    # )  TODO: Azure storage integration is coming soon
    git: typing.Optional[StorageGit] = pydantic.Field(
        default=None,
        examples=[
            None,
            None,
            None,
            {
                "repo_id": "my-repo-id",
                "repo": {
                    "name": "test-dataset",
                    "repository_url": "https://github.com/Hirundo-io/test-dataset.git",
                },
                "branch": "main",
                "path": "/my-path/to/dataset",
            },
        ],
    )
    """
    The Git storage integration details.
    Use this if you want to link to a Git repository.
    """

    @staticmethod
    def get_by_id(storage_integration_id: int) -> "ResponseStorageIntegration":
        """
        Retrieves a `StorageIntegration` instance from the server by its ID

        Args:
            storage_integration_id: The ID of the `StorageIntegration` to retrieve
        """
        storage_integration = requests.get(
            f"{API_HOST}/storage-integration/{storage_integration_id}",
            headers=get_auth_headers(),
            timeout=READ_TIMEOUT,
        )
        raise_for_status_with_reason(storage_integration)
        return ResponseStorageIntegration(**storage_integration.json())

    @staticmethod
    def get_by_name(
        name: str, storage_type: StorageTypes
    ) -> "ResponseStorageIntegration":
        """
        Retrieves a `StorageIntegration` instance from the server by its name

        Args:
            name: The name of the `StorageIntegration` to retrieve
            storage_type: The type of the `StorageIntegration` to retrieve

            Note: The type is required because the name is not unique across different storage types
        """
        storage_integration = requests.get(
            f"{API_HOST}/storage-integration/by-name/{name}?storage_type={storage_type}",
            headers=get_auth_headers(),
            timeout=READ_TIMEOUT,
        )
        raise_for_status_with_reason(storage_integration)
        return ResponseStorageIntegration(**storage_integration.json())

    @staticmethod
    def list(
        organization_id: typing.Optional[int] = None,
    ) -> list["ResponseStorageIntegration"]:
        """
        Lists all the `StorageIntegration`'s created by user's default organization
        Note: The return type is `list[dict]` and not `list[StorageIntegration]`

        Args:
            organization_id: The ID of the organization to list `StorageIntegration`'s for.
            If not provided, it will list `StorageIntegration`'s for the default organization.
        """
        storage_integrations = requests.get(
            f"{API_HOST}/storage-integration/",
            params={"storage_integration_organization_id": organization_id},
            headers=get_auth_headers(),
            timeout=READ_TIMEOUT,
        )
        raise_for_status_with_reason(storage_integrations)
        return [ResponseStorageIntegration(**si) for si in storage_integrations.json()]

    @staticmethod
    def delete_by_id(storage_integration_id) -> None:
        """
        Deletes a `StorageIntegration` instance from the server by its ID

        Args:
            storage_integration_id: The ID of the `StorageIntegration` to delete
        """
        storage_integration = requests.delete(
            f"{API_HOST}/storage-integration/{storage_integration_id}",
            headers=get_auth_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(storage_integration)
        logger.info("Deleted storage integration with ID: %s", storage_integration_id)

    def delete(self) -> None:
        """
        Deletes the `StorageIntegration` instance from the server
        """
        if not self.id:
            raise ValueError("No StorageIntegration has been created")
        self.delete_by_id(self.id)

    def create(self, replace_if_exists: bool = False) -> int:
        """
        Create a `StorageIntegration` instance on the server
        """
        if self.git and self.git.repo:
            self.git.repo_id = self.git.repo.create()
        storage_integration = requests.post(
            f"{API_HOST}/storage-integration/",
            json={
                **self.model_dump(mode="json"),
                "replace_if_exists": replace_if_exists,
            },
            headers={
                **json_headers,
                **get_auth_headers(),
            },
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(storage_integration)
        storage_integration_id = storage_integration.json()["id"]
        self.id = storage_integration_id
        logger.info("Created storage integration with ID: %s", storage_integration_id)
        return storage_integration_id

    @model_validator(mode="after")
    def validate_storage_type(self):
        if self.type != StorageTypes.LOCAL and (
            [self.s3, self.gcp, self.git].count(None) != 2
        ):
            raise ValueError("Exactly one of S3, GCP, or Git must be provided")
        if self.type == StorageTypes.S3 and self.s3 is None:
            raise ValueError("S3 storage details must be provided")
        elif self.type == StorageTypes.GCP and self.gcp is None:
            raise ValueError("GCP storage details must be provided")
        elif self.type == StorageTypes.GIT and self.git is None:
            raise ValueError("Git storage details must be provided")
        if not self.type and not any([self.s3, self.gcp, self.git]):
            raise ValueError("Storage type must be provided")
        elif not self.type:
            self.type = (
                StorageTypes.S3
                if self.s3 is not None
                else StorageTypes.GCP
                if self.gcp is not None
                else StorageTypes.GIT
                if self.git is not None
                else StorageTypes.LOCAL
            )
        return self


class ResponseStorageIntegration(BaseModel):
    id: int
    name: StorageIntegrationName
    type: StorageTypes
    organization_name: str
    creator_name: str
    s3: typing.Optional[StorageS3Out]
    gcp: typing.Optional[StorageGCPOut]
    # azure: typing.Optional[StorageAzureOut]
    git: typing.Optional[StorageGitOut]
