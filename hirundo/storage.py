import typing
from enum import Enum
from typing import Union

import pydantic
import requests
from pydantic import BaseModel, model_validator
from pydantic_core import Url

from hirundo._constraints import S3BucketUrl, StorageIntegrationName
from hirundo._env import API_HOST
from hirundo._headers import auth_headers, json_headers
from hirundo._timeouts import MODIFY_TIMEOUT, READ_TIMEOUT
from hirundo.git import GitRepo


class StorageS3(BaseModel):
    endpoint_url: Union[Url, None] = None
    bucket_url: S3BucketUrl
    region_name: str
    # ⬆️ We could restrict this, but if we're allowing custom endpoints then the validation may be wrong
    access_key_id: Union[str, None] = None
    secret_access_key: Union[str, None] = None


class StorageGCP(BaseModel):
    bucket_name: str
    project: str
    credentials_json: Union[dict, None] = None


# TODO: Azure storage integration is coming soon
# class StorageAzure(BaseModel):
#     container: str
#     account_name: str
#     account_key: str


class StorageGit(BaseModel):
    repo_id: Union[int, None] = None
    """
    The ID of the Git repository in the Hirundo system.
    Either `repo_id` or `repo` must be provided.
    """
    repo: Union[GitRepo, None] = None
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


class StorageTypes(str, Enum):
    """
    Enum for the different types of storage integrations.
    Supported types are:
    """

    S3 = "S3"
    GCP = "GCP"
    # AZURE = "Azure"  TODO: Azure storage integration is coming soon
    GIT = "Git"


class StorageIntegration(BaseModel):
    id: Union[int, None] = None

    organization_id: Union[int, None] = None
    """
    The ID of the organization that the `StorageIntegration` belongs to.
    If not provided, it will be assigned to your default organization.
    """

    name: StorageIntegrationName
    """
    A name to identify the `StorageIntegration` in the Hirundo system.
    """
    type: StorageTypes = pydantic.Field(
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
    s3: Union[StorageS3, None] = pydantic.Field(
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
    gcp: Union[StorageGCP, None] = pydantic.Field(
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
    # azure: Union[StorageAzure, None] = pydantic.Field(
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
    git: Union[StorageGit, None] = pydantic.Field(
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
    def list(organization_id: typing.Union[int, None] = None) -> list[dict]:
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
            headers=auth_headers,
            timeout=READ_TIMEOUT,
        )
        storage_integrations.raise_for_status()
        return storage_integrations.json()

    @staticmethod
    def delete_by_id(storage_integration_id) -> None:
        """
        Deletes a `StorageIntegration` instance from the server by its ID

        Args:
            storage_integration_id: The ID of the `StorageIntegration` to delete
        """
        storage_integration = requests.delete(
            f"{API_HOST}/storage-integration/{storage_integration_id}",
            headers=auth_headers,
            timeout=MODIFY_TIMEOUT,
        )
        storage_integration.raise_for_status()

    def delete(self) -> None:
        """
        Deletes the `StorageIntegration` instance from the server
        """
        if not self.id:
            raise ValueError("No StorageIntegration has been created")
        self.delete_by_id(self.id)

    def create(self) -> int:
        """
        Create a `StorageIntegration` instance on the server
        """
        if self.git and self.git.repo:
            self.git.repo_id = self.git.repo.create()
        storage_integration = requests.post(
            f"{API_HOST}/storage-integration/",
            json=self.model_dump(),
            headers={
                **json_headers,
                **auth_headers,
            },
            timeout=MODIFY_TIMEOUT,
        )
        storage_integration.raise_for_status()
        storage_integration_id = storage_integration.json()["id"]
        self.id = storage_integration_id
        return storage_integration_id


class StorageLink(BaseModel):
    storage_integration: StorageIntegration
    """
    The `StorageIntegration` instance to link to.
    """
    path: str = "/"
    """
    Path for the `root` to link to within the `StorageIntegration` instance,
    e.g. a prefix path/folder within an S3 Bucket / GCP Bucket / Azure Blob storage / Git repo.

    Note: Only files in this path will be retrieved and it will be used as the root for paths in the CSV.
    """
