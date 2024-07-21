from typing import Annotated

from pydantic import StringConstraints

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
