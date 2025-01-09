import re
import typing
from typing import TYPE_CHECKING

from hirundo._urls import (
    GCP_BUCKET_MAX_LENGTH,
    GCP_MAX_LENGTH,
    GCP_MIN_LENGTH,
    GCP_PATTERN,
    S3_MAX_LENGTH,
    S3_MIN_LENGTH,
    S3_PATTERN,
)
from hirundo.labeling import COCO, YOLO, HirundoCSV, Keylabs
from hirundo.storage import StorageTypes

if TYPE_CHECKING:
    from hirundo._urls import HirundoUrl
    from hirundo.dataset_optimization import LabelingInfo
    from hirundo.storage import ResponseStorageConfig, StorageConfig


def validate_url(
    url: "HirundoUrl",
    storage_config: "StorageConfig | ResponseStorageConfig",
) -> "HirundoUrl":
    is_s3 = storage_config.s3 is not None
    is_gcp = storage_config.gcp is not None
    matches = None

    if is_s3 and len(str(url)) < S3_MIN_LENGTH or len(str(url)) > S3_MAX_LENGTH:
        raise ValueError("S3 URL must be between 8 and 1023 characters")
    elif is_s3 and not re.match(S3_PATTERN, str(url)):
        raise ValueError("Invalid S3 URL")
    elif storage_config.s3 is not None and not str(url).startswith(
        f"{storage_config.s3.bucket_url}/"
    ):
        #  New `storage_config.s3` check because `is_s3` is not enough for Pylance
        raise ValueError(f"S3 URL must start with {storage_config.s3.bucket_url}/")
    elif is_gcp and len(str(url)) < GCP_MIN_LENGTH or len(str(url)) > GCP_MAX_LENGTH:
        raise ValueError("GCP URL must be between 8 and 1023 characters")
    elif is_gcp and not (matches := re.match(GCP_PATTERN, str(url))):
        raise ValueError("Invalid GCP URL")
    elif is_gcp and matches and len(matches.group(1)) > GCP_BUCKET_MAX_LENGTH:
        raise ValueError("GCP bucket name must be between 3 and 222 characters")
    elif storage_config.gcp is not None and not str(url).startswith(
        f"gs://{storage_config.gcp.bucket_name}/"
    ):
        #  New `storage_config.gcp` check because `is_gcp` is not enough for Pylance
        raise ValueError(
            f"GCP URL must start with gs://{storage_config.gcp.bucket_name}"
        )
    elif (
        storage_config.git is not None
        and not str(url).startswith("https://")
        and not str(url).startswith("ssh://")
    ):
        raise ValueError("Git URL must start with https:// or ssh://")
    elif storage_config.type == StorageTypes.LOCAL and not str(url).startswith(
        "file:///datasets/"
    ):
        raise ValueError("Local URL must start with file:///datasets/")
    return url


def validate_labeling_info(
    labeling_info: "typing.Union[LabelingInfo, list[LabelingInfo]]",
    storage_config: "typing.Union[StorageConfig, ResponseStorageConfig]",
) -> None:
    if isinstance(labeling_info, list):
        for labeling in labeling_info:
            validate_labeling_info(labeling, storage_config)
    elif isinstance(labeling_info, HirundoCSV):
        validate_url(labeling_info.csv_url, storage_config)
    elif isinstance(labeling_info, COCO):
        validate_url(labeling_info.json_url, storage_config)
    elif isinstance(labeling_info, YOLO):
        validate_url(labeling_info.labels_dir_url, storage_config)
        if labeling_info.data_yaml_url is not None:
            validate_url(labeling_info.data_yaml_url, storage_config)
    elif isinstance(labeling_info, Keylabs):
        validate_url(labeling_info.labels_dir_url, storage_config)
