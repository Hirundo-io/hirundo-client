from typing import Annotated, Union

from pydantic import FileUrl, HttpUrl, StringConstraints, UrlConstraints

S3BucketUrl = Annotated[
    str,
    StringConstraints(
        min_length=8,
        max_length=1023,
        pattern=r"s3?://[a-z0-9.-]{3,64}[/]?",  # Only allow real S3 bucket URLs
    ),
]

StorageIntegrationName = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=255,
        pattern=r"^[a-zA-Z0-9-_]+$",
    ),
]

S3_MIN_LENGTH = 8
S3_MAX_LENGTH = 1023
S3_PATTERN = r"s3://[a-zA-Z0-9.-]{3,64}/[a-zA-Z0-9.-/]+"
GCP_MIN_LENGTH = 8
GCP_MAX_LENGTH = 1023
GCP_PATTERN = r"gs://[a-zA-Z0-9.-]{3,64}/[a-zA-Z0-9.-/]+"

S3ObjectUrl = Annotated[
    str,
    UrlConstraints(),
    StringConstraints(
        min_length=S3_MIN_LENGTH,
        max_length=S3_MAX_LENGTH,
        pattern=S3_PATTERN,
    ),
]
GCPObjectUrl = Annotated[
    str,
    UrlConstraints(),
    StringConstraints(
        min_length=8,
        max_length=1023,
        pattern=GCP_PATTERN,
    ),
]
SSHUrl = Annotated[str, UrlConstraints(allowed_schemes=["ssh"])]

HirundoUrl = Union[FileUrl, HttpUrl, S3ObjectUrl, GCPObjectUrl, SSHUrl]
