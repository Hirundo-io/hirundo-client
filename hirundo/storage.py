from enum import Enum
from pydantic import BaseModel
import pydantic
from pydantic_core import Url
import requests

from hirundo.constraints import S3BucketUrl, StorageIntegrationName
from hirundo.headers import auth_headers, json_headers
from hirundo.env import API_HOST
from hirundo.git import GitRepo


class StorageS3(BaseModel):
    endpoint_url: Url | None = None
    bucket_url: S3BucketUrl
    region_name: str
    # ⬆️ We could restrict this, but if we're allowing custom endpoints then the validation may be wrong
    access_key_id: str | None = None
    secret_access_key: str | None = None


class StorageGCP(BaseModel):
    bucket: str
    project: str
    credentials_json: dict | None


class StorageAzure(BaseModel):
    container: str
    account_name: str
    account_key: str


class StorageGit(BaseModel):
    repo_id: int
    repo: GitRepo
    branch: str
    path: str


class StorageTypes(str, Enum):
    S3 = "S3"
    GCP = "GCP"
    AZURE = "Azure"
    GIT = "Git"


class StorageIntegration(BaseModel):
    owner_id: int | None = None

    name: StorageIntegrationName
    type: StorageTypes
    s3: StorageS3 | None = pydantic.Field(
        default=None,
        examples=[
            {
                "bucket_url": "s3://my-bucket",
                "region_name": "us-west-2",
                "access_key_id": "my-access-key",
                "secret_access_key": "REDACTED",
            },
            None,
        ],
    )
    gcp: StorageGCP | None = pydantic.Field(
        default=None,
        examples=[
            None,
            None,
        ],
    )
    azure: StorageAzure | None = pydantic.Field(
        default=None,
        examples=[
            None,
            {
                "container": "my-container",
                "account_name": "my-account-name",
                "account_key": "my-account",
            },
        ],
    )
    git: StorageGit | None = pydantic.Field(
        default=None,
        examples=[
            None,
            None,
        ],
    )

    @staticmethod
    def list():
        storage_integrations = requests.get(
            f"{API_HOST}/storage-integration/",
            headers=auth_headers,
        )
        storage_integrations.raise_for_status()
        return storage_integrations.json()
    
    @staticmethod
    def delete_by_id(storage_integration_id):
        storage_integration = requests.delete(
            f"{API_HOST}/storage-integration/{storage_integration_id}",
            headers=auth_headers,
        )
        storage_integration.raise_for_status()

    def create(self):
        storage_integration = requests.post(
            f"{API_HOST}/storage-integration/",
            json=self.model_dump(),
            headers={
                **json_headers,
                **auth_headers,
            },
        )
        storage_integration.raise_for_status()
        return storage_integration.json()["id"]


class StorageLink(BaseModel):
    storage_integration: StorageIntegration
    path: str = "/"
