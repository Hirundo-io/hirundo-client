import re
import typing
from typing import TYPE_CHECKING

from hirundo._urls import (
    LENGTH_CONSTRAINTS,
    STORAGE_PATTERNS,
)
from hirundo.enum import DatasetMetadataType, LabelingType, StorageTypes
from hirundo.labeling import COCO, YOLO, HirundoCSV, Keylabs

if TYPE_CHECKING:
    from hirundo._urls import HirundoUrl
    from hirundo.dataset_optimization import LabelingInfo
    from hirundo.storage import ResponseStorageConfig, StorageConfig

LABELING_TYPES_TO_DATASET_METADATA_TYPES = {
    LabelingType.SINGLE_LABEL_CLASSIFICATION: [
        DatasetMetadataType.HIRUNDO_CSV,
    ],
    LabelingType.OBJECT_DETECTION: [
        DatasetMetadataType.HIRUNDO_CSV,
        DatasetMetadataType.COCO,
        DatasetMetadataType.YOLO,
        DatasetMetadataType.KeylabsObjDetImages,
        DatasetMetadataType.KeylabsObjDetVideo,
    ],
    LabelingType.OBJECT_SEGMENTATION: [
        DatasetMetadataType.HIRUNDO_CSV,
        DatasetMetadataType.KeylabsObjSegImages,
        DatasetMetadataType.KeylabsObjSegVideo,
    ],
    LabelingType.SEMANTIC_SEGMENTATION: [
        DatasetMetadataType.HIRUNDO_CSV,
    ],
    LabelingType.PANOPTIC_SEGMENTATION: [
        DatasetMetadataType.HIRUNDO_CSV,
    ],
}


def validate_url(
    url: "HirundoUrl",
    storage_config: "StorageConfig | ResponseStorageConfig",
) -> "HirundoUrl":
    is_s3 = storage_config.s3 is not None
    is_gcp = storage_config.gcp is not None
    matches = None

    if is_s3 and (
        len(str(url)) < LENGTH_CONSTRAINTS[StorageTypes.S3]["min_length"]
        or len(str(url)) > LENGTH_CONSTRAINTS[StorageTypes.S3]["max_length"]
    ):
        raise ValueError("S3 URL must be between 8 and 1023 characters")
    elif is_s3 and not re.match(STORAGE_PATTERNS[StorageTypes.S3], str(url)):
        raise ValueError("Invalid S3 URL")
    elif storage_config.s3 is not None and not str(url).startswith(
        f"{storage_config.s3.bucket_url}/"
    ):
        #  New `storage_config.s3` check because `is_s3` is not enough for Pylance
        raise ValueError(f"S3 URL must start with {storage_config.s3.bucket_url}/")
    elif is_gcp and (
        len(str(url)) < LENGTH_CONSTRAINTS[StorageTypes.GCP]["min_length"]
        or len(str(url)) > LENGTH_CONSTRAINTS[StorageTypes.GCP]["max_length"]
    ):
        raise ValueError("GCP URL must be between 8 and 1023 characters")
    elif is_gcp and not (
        matches := re.match(STORAGE_PATTERNS[StorageTypes.GCP], str(url))
    ):
        raise ValueError("Invalid GCP URL")
    elif (
        is_gcp
        and matches
        and len(matches.group(1))
        > LENGTH_CONSTRAINTS[StorageTypes.GCP]["bucket_max_length"]
    ):
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


def validate_labeling_type(
    labeling_type: "LabelingType", labeling_info: "LabelingInfo"
) -> None:
    """
    Validate that the labeling type is compatible with the labeling info

    Args:
        labeling_type: The type of labeling that will be performed
        labeling_info: The labeling info to validate
    """
    dataset_metadata_types = LABELING_TYPES_TO_DATASET_METADATA_TYPES[labeling_type]
    if labeling_info.type not in dataset_metadata_types:
        raise ValueError(
            f"Cannot use {labeling_info.type.name} labeling info with {labeling_type.name} datasets"
        )


def validate_labeling_info(
    labeling_type: "LabelingType",
    labeling_info: "typing.Union[LabelingInfo, list[LabelingInfo]]",
    storage_config: "typing.Union[StorageConfig, ResponseStorageConfig]",
) -> None:
    """
    Validate the labeling info for a dataset

    Args:
        labeling_type: The type of labeling that will be performed
        labeling_info: The labeling info to validate
        storage_config: The storage configuration for the dataset.
            StorageConfig is used to validate the URLs in the labeling info
    """
    if isinstance(labeling_info, list):
        for labeling in labeling_info:
            validate_labeling_info(labeling_type, labeling, storage_config)
        return
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
    validate_labeling_type(labeling_type, labeling_info)
