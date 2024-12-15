import datetime
import json
import typing
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Generator
from enum import Enum
from io import StringIO
from typing import overload

import httpx
import numpy as np
import pandas as pd
import requests
from pandas._typing import DtypeArg
from pydantic import BaseModel, Field, model_validator
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from hirundo._constraints import HirundoUrl
from hirundo._env import API_HOST
from hirundo._headers import get_auth_headers, json_headers
from hirundo._http import raise_for_status_with_reason
from hirundo._iter_sse_retrying import aiter_sse_retrying, iter_sse_retrying
from hirundo._timeouts import MODIFY_TIMEOUT, READ_TIMEOUT
from hirundo.enum import DatasetMetadataType, LabelingType
from hirundo.logger import get_logger
from hirundo.storage import ResponseStorageConfig, StorageConfig

logger = get_logger(__name__)


class HirundoError(Exception):
    """
    Custom exception used to indicate errors in `hirundo` dataset optimization runs
    """

    pass


MAX_RETRIES = 200  # Max 200 retries for HTTP SSE connection


class RunStatus(Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    AWAITING_MANUAL_APPROVAL = "AWAITING MANUAL APPROVAL"
    REVOKED = "REVOKED"
    REJECTED = "REJECTED"
    RETRY = "RETRY"


STATUS_TO_TEXT_MAP = {
    RunStatus.STARTED.value: "Optimization run in progress. Downloading dataset",
    RunStatus.PENDING.value: "Optimization run queued and not yet started",
    RunStatus.SUCCESS.value: "Optimization run completed successfully",
    RunStatus.FAILURE.value: "Optimization run failed",
    RunStatus.AWAITING_MANUAL_APPROVAL.value: "Awaiting manual approval",
    RunStatus.RETRY.value: "Optimization run failed. Retrying",
    RunStatus.REVOKED.value: "Optimization run was cancelled",
    RunStatus.REJECTED.value: "Optimization run was rejected",
}
STATUS_TO_PROGRESS_MAP = {
    RunStatus.STARTED.value: 0.0,
    RunStatus.PENDING.value: 0.0,
    RunStatus.SUCCESS.value: 100.0,
    RunStatus.FAILURE.value: 100.0,
    RunStatus.AWAITING_MANUAL_APPROVAL.value: 100.0,
    RunStatus.RETRY.value: 0.0,
    RunStatus.REVOKED.value: 100.0,
    RunStatus.REJECTED.value: 0.0,
}


class DatasetOptimizationResults(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    suspects: pd.DataFrame
    """
    A pandas DataFrame containing the results of the optimization run
    """
    warnings_and_errors: pd.DataFrame
    """
    A pandas DataFrame containing the warnings and errors of the optimization run
    """


CUSTOMER_INTERCHANGE_DTYPES: DtypeArg = {
    "image_path": str,
    "label_path": str,
    "segments_mask_path": str,
    "segment_id": np.int32,
    "label": str,
    "bbox_id": str,
    "xmin": np.float32,
    "ymin": np.float32,
    "xmax": np.float32,
    "ymax": np.float32,
    "suspect_level": np.float32,  # If exists, must be one of the values in the enum below
    "suggested_label": str,
    "suggested_label_conf": np.float32,
    "status": str,
    # ⬆️ If exists, must be one of the following:
    # NO_LABELS/MISSING_IMAGE/INVALID_IMAGE/INVALID_BBOX/INVALID_BBOX_SIZE/INVALID_SEG/INVALID_SEG_SIZE
}


class Metadata(BaseModel, ABC):
    type: DatasetMetadataType

    @property
    @abstractmethod
    def metadata_url(self) -> HirundoUrl:
        raise NotImplementedError()


class HirundoCSV(Metadata):
    """
    A dataset metadata file in the Hirundo CSV format
    """

    type: DatasetMetadataType = DatasetMetadataType.HIRUNDO_CSV
    csv_url: HirundoUrl
    """
    The URL to access the dataset metadata CSV file.
    e.g. `s3://my-bucket-name/my-folder/my-metadata.csv`, `gs://my-bucket-name/my-folder/my-metadata.csv`,
    or `ssh://my-username@my-repo-name/my-folder/my-metadata.csv`
    (or `file:///datasets/my-folder/my-metadata.csv` if using LOCAL storage type with on-premises installation)
    """

    @property
    def metadata_url(self) -> HirundoUrl:
        return self.csv_url


class COCO(Metadata):
    """
    A dataset metadata file in the COCO format
    """

    type: DatasetMetadataType = DatasetMetadataType.COCO
    json_url: HirundoUrl
    """
    The URL to access the dataset metadata JSON file.
    e.g. `s3://my-bucket-name/my-folder/my-metadata.json`, `gs://my-bucket-name/my-folder/my-metadata.json`,
    or `ssh://my-username@my-repo-name/my-folder/my-metadata.json`
    (or `file:///datasets/my-folder/my-metadata.json` if using LOCAL storage type with on-premises installation)
    """

    @property
    def metadata_url(self) -> HirundoUrl:
        return self.json_url


class YOLO(Metadata):
    type: DatasetMetadataType = DatasetMetadataType.YOLO
    data_yaml_url: typing.Optional[HirundoUrl] = None
    labels_dir_url: HirundoUrl

    @property
    def metadata_url(self) -> HirundoUrl:
        return self.labels_dir_url


LabelingInfo = typing.Union[HirundoCSV, COCO, YOLO]
"""
The dataset labeling info. The dataset labeling info can be one of the following:
- `DatasetMetadataType.HirundoCSV`: Indicates that the dataset metadata file is a CSV file with the Hirundo format

Currently no other formats are supported. Future versions of `hirundo` may support additional formats.
"""


class VisionRunArgs(BaseModel):
    upsample: bool = False
    """
    Whether to upsample the dataset to attempt to balance the classes.
    """
    min_abs_bbox_size: int = 0
    """
    Minimum valid size (in pixels) of a bounding box to keep it in the dataset for optimization.
    """
    min_abs_bbox_area: int = 0
    """
    Minimum valid absolute area (in pixels²) of a bounding box to keep it in the dataset for optimization.
    """
    min_rel_bbox_size: float = 0.0
    """
    Minimum valid size (as a fraction of both image height and width) for a bounding box
    to keep it in the dataset for optimization, relative to the corresponding dimension size,
    i.e. if the bounding box is 10% of the image width and 5% of the image height, it will be kept if this value is 0.05, but not if the
    value is 0.06 (since both width and height are checked).
    """
    min_rel_bbox_area: float = 0.0
    """
    Minimum valid relative area (as a fraction of the image area) of a bounding box to keep it in the dataset for optimization.
    """


RunArgs = typing.Union[VisionRunArgs]


class AugmentationNames(str, Enum):
    RandomHorizontalFlip = "RandomHorizontalFlip"
    RandomVerticalFlip = "RandomVerticalFlip"
    RandomRotation = "RandomRotation"
    ColorJitter = "ColorJitter"
    RandomAffine = "RandomAffine"
    RandomPerspective = "RandomPerspective"


class Modality(str, Enum):
    IMAGE = "Image"
    RADAR = "Radar"
    EKG = "EKG"


class OptimizationDataset(BaseModel):
    id: typing.Optional[int] = Field(default=None)
    """
    The ID of the dataset created on the server.
    """
    name: str
    """
    The name of the dataset. Used to identify it amongst the list of datasets
    belonging to your organization in `hirundo`.
    """
    labeling_type: LabelingType
    """
    Indicates the labeling type of the dataset. The labeling type can be one of the following:
    - `LabelingType.SINGLE_LABEL_CLASSIFICATION`: Indicates that the dataset is for classification tasks
    - `LabelingType.OBJECT_DETECTION`: Indicates that the dataset is for object detection tasks
    - `LabelingType.SPEECH_TO_TEXT`: Indicates that the dataset is for speech-to-text tasks
    """
    language: typing.Optional[str] = None
    """
    Language of the Speech-to-Text audio dataset. This is required for Speech-to-Text datasets.
    """
    storage_config_id: typing.Optional[int] = None
    """
    The ID of the storage config used to store the dataset and metadata.
    """
    storage_config: typing.Optional[
        typing.Union[StorageConfig, ResponseStorageConfig]
    ] = None
    """
    The `StorageConfig` instance to link to.
    """
    data_root_url: HirundoUrl
    """
    URL for data (e.g. images) within the `StorageConfig` instance,
    e.g. `s3://my-bucket-name/my-images-folder`, `gs://my-bucket-name/my-images-folder`,
    or `ssh://my-username@my-repo-name/my-images-folder`
    (or `file:///datasets/my-images-folder` if using LOCAL storage type with on-premises installation)

    Note: All CSV `image_path` entries in the metadata file should be relative to this folder.
    """

    classes: typing.Optional[list[str]] = None
    """
    A full list of possible classes used in classification / object detection.
    It is currently required for clarity and performance.
    """
    labeling_info: LabelingInfo

    augmentations: typing.Optional[list[AugmentationNames]] = None
    """
    Used to define which augmentations are apply to a vision dataset.
    For audio datasets, this field is ignored.
    If no value is provided, all augmentations are applied to vision datasets.
    """
    modality: Modality = Modality.IMAGE
    """
    Used to define the modality of the dataset.
    Defaults to Image.
    """

    run_id: typing.Optional[str] = Field(default=None, init=False)
    """
    The ID of the Dataset Optimization run created on the server.
    """

    status: typing.Optional[RunStatus] = None

    @model_validator(mode="after")
    def validate_dataset(self):
        if self.storage_config is None and self.storage_config_id is None:
            raise ValueError(
                "No dataset storage has been provided. Provide one via `storage_config` or `storage_config_id`"
            )
        elif self.storage_config is not None and self.storage_config_id is not None:
            raise ValueError(
                "Both `storage_config` and `storage_config_id` have been provided. Pick one."
            )
        if self.labeling_type == LabelingType.SPEECH_TO_TEXT and self.language is None:
            raise ValueError("Language is required for Speech-to-Text datasets.")
        elif (
            self.labeling_type != LabelingType.SPEECH_TO_TEXT
            and self.language is not None
        ):
            raise ValueError("Language is only allowed for Speech-to-Text datasets.")
        if (
            self.labeling_info.type == DatasetMetadataType.YOLO
            and isinstance(self.labeling_info, YOLO)
            and (
                self.labeling_info.data_yaml_url is not None
                and self.classes is not None
            )
        ):
            raise ValueError(
                "Only one of `classes` or `labeling_info.data_yaml_url` should be provided for YOLO datasets"
            )
        return self

    @staticmethod
    def get_by_id(dataset_id: int) -> "OptimizationDataset":
        """
        Get a `OptimizationDataset` instance from the server by its ID

        Args:
            dataset_id: The ID of the `OptimizationDataset` instance to get
        """
        response = requests.get(
            f"{API_HOST}/dataset-optimization/dataset/{dataset_id}",
            headers=get_auth_headers(),
            timeout=READ_TIMEOUT,
        )
        raise_for_status_with_reason(response)
        dataset = response.json()
        return OptimizationDataset(**dataset)

    @staticmethod
    def get_by_name(name: str) -> "OptimizationDataset":
        """
        Get a `OptimizationDataset` instance from the server by its name

        Args:
            name: The name of the `OptimizationDataset` instance to get
        """
        response = requests.get(
            f"{API_HOST}/dataset-optimization/dataset/by-name/{name}",
            headers=get_auth_headers(),
            timeout=READ_TIMEOUT,
        )
        raise_for_status_with_reason(response)
        dataset = response.json()
        return OptimizationDataset(**dataset)

    @staticmethod
    def list_datasets(
        organization_id: typing.Optional[int] = None,
    ) -> list["DataOptimizationDatasetOut"]:
        """
        Lists all the optimization datasets created by user's default organization
        or the `organization_id` passed

        Args:
            organization_id: The ID of the organization to list the datasets for.
        """
        response = requests.get(
            f"{API_HOST}/dataset-optimization/dataset/",
            params={"dataset_organization_id": organization_id},
            headers=get_auth_headers(),
            timeout=READ_TIMEOUT,
        )
        raise_for_status_with_reason(response)
        datasets = response.json()
        return [
            DataOptimizationDatasetOut(
                **ds,
            )
            for ds in datasets
        ]

    @staticmethod
    def list_runs(
        organization_id: typing.Optional[int] = None,
    ) -> list["DataOptimizationRunOut"]:
        """
        Lists all the `OptimizationDataset` instances created by user's default organization
        or the `organization_id` passed
        Note: The return type is `list[dict]` and not `list[OptimizationDataset]`

        Args:
            organization_id: The ID of the organization to list the datasets for.
        """
        response = requests.get(
            f"{API_HOST}/dataset-optimization/run/list",
            params={"dataset_organization_id": organization_id},
            headers=get_auth_headers(),
            timeout=READ_TIMEOUT,
        )
        raise_for_status_with_reason(response)
        runs = response.json()
        return [
            DataOptimizationRunOut(
                **run,
            )
            for run in runs
        ]

    @staticmethod
    def delete_by_id(dataset_id: int) -> None:
        """
        Deletes a `OptimizationDataset` instance from the server by its ID

        Args:
            dataset_id: The ID of the `OptimizationDataset` instance to delete
        """
        response = requests.delete(
            f"{API_HOST}/dataset-optimization/dataset/{dataset_id}",
            headers=get_auth_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(response)
        logger.info("Deleted dataset with ID: %s", dataset_id)

    def delete(self, storage_config=True) -> None:
        """
        Deletes the active `OptimizationDataset` instance from the server.
        It can only be used on a `OptimizationDataset` instance that has been created.

        Args:
            storage_config: If True, the `OptimizationDataset`'s `StorageConfig` will also be deleted

        Note: If `storage_config` is not set to `False` then the `storage_config_id` must be set
        This can either be set manually or by creating the `StorageConfig` instance via the `OptimizationDataset`'s
        `create` method
        """
        if storage_config:
            if not self.storage_config_id:
                raise ValueError("No storage config has been created")
            StorageConfig.delete_by_id(self.storage_config_id)
        if not self.id:
            raise ValueError("No dataset has been created")
        self.delete_by_id(self.id)

    def create(
        self,
        organization_id: typing.Optional[int] = None,
        replace_if_exists: bool = False,
    ) -> int:
        """
        Create a `OptimizationDataset` instance on the server.
        If the `storage_config_id` field is not set, the storage config will also be created and the field will be set.

        Args:
            organization_id: The ID of the organization to create the dataset for.
            replace_if_exists: If True, the dataset will be replaced if it already exists
                (this is determined by a dataset of the same name in the same organization).

        Returns:
            The ID of the created `OptimizationDataset` instance
        """
        if self.storage_config is None and self.storage_config_id is None:
            raise ValueError("No dataset storage has been provided")
        elif self.storage_config and self.storage_config_id is None:
            if isinstance(self.storage_config, ResponseStorageConfig):
                self.storage_config_id = self.storage_config.id
            elif isinstance(self.storage_config, StorageConfig):
                self.storage_config_id = self.storage_config.create(
                    replace_if_exists=replace_if_exists,
                )
        elif (
            self.storage_config is not None
            and self.storage_config_id is not None
            and (
                not isinstance(self.storage_config, ResponseStorageConfig)
                or self.storage_config.id != self.storage_config_id
            )
        ):
            raise ValueError(
                "Both `storage_config` and `storage_config_id` have been provided. Storage config IDs do not match."
            )
        model_dict = self.model_dump(mode="json")
        # ⬆️ Get dict of model fields from Pydantic model instance
        dataset_response = requests.post(
            f"{API_HOST}/dataset-optimization/dataset/",
            json={
                **{k: model_dict[k] for k in model_dict.keys() - {"storage_config"}},
                "organization_id": organization_id,
                "replace_if_exists": replace_if_exists,
            },
            headers={
                **json_headers,
                **get_auth_headers(),
            },
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(dataset_response)
        self.id = dataset_response.json()["id"]
        if not self.id:
            raise HirundoError("An error ocurred while trying to create the dataset")
        logger.info("Created dataset with ID: %s", self.id)
        return self.id

    @staticmethod
    def launch_optimization_run(
        dataset_id: int,
        organization_id: typing.Optional[int] = None,
        run_args: typing.Optional[RunArgs] = None,
    ) -> str:
        """
        Run the dataset optimization process on the server using the dataset with the given ID
        i.e. `dataset_id`.

        Args:
            dataset_id: The ID of the dataset to run optimization on.

        Returns:
            ID of the run (`run_id`).
        """
        run_info = {}
        if organization_id:
            run_info["organization_id"] = organization_id
        if run_args:
            run_info["run_args"] = run_args.model_dump(mode="json")
        run_response = requests.post(
            f"{API_HOST}/dataset-optimization/run/{dataset_id}",
            json=run_info if len(run_info) > 0 else None,
            headers=get_auth_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(run_response)
        return run_response.json()["run_id"]

    def _validate_run_args(self, run_args: RunArgs) -> None:
        if self.labeling_type == LabelingType.SPEECH_TO_TEXT:
            raise Exception("Speech to text cannot have `run_args` set")
        if self.labeling_type != LabelingType.OBJECT_DETECTION and any(
            (
                run_args.min_abs_bbox_size != 0,
                run_args.min_abs_bbox_area != 0,
                run_args.min_rel_bbox_size != 0,
                run_args.min_rel_bbox_area != 0,
            )
        ):
            raise Exception(
                "Cannot set `min_abs_bbox_size`, `min_abs_bbox_area`, "
                + "`min_rel_bbox_size`, or `min_rel_bbox_area` for "
                + f"labeling type {self.labeling_type}"
            )

    def run_optimization(
        self,
        organization_id: typing.Optional[int] = None,
        replace_dataset_if_exists: bool = False,
        run_args: typing.Optional[RunArgs] = None,
    ) -> str:
        """
        If the dataset was not created on the server yet, it is created.
        Run the dataset optimization process on the server using the active `OptimizationDataset` instance

        Args:
            organization_id: The ID of the organization to run the optimization for.
            replace_dataset_if_exists: If True, the dataset will be replaced if it already exists
                (this is determined by a dataset of the same name in the same organization).
            run_args: The run arguments to use for the optimization run

        Returns:
            An ID of the run (`run_id`) and stores that `run_id` on the instance
        """
        try:
            if not self.id:
                self.id = self.create(replace_if_exists=replace_dataset_if_exists)
            if run_args is not None:
                self._validate_run_args(run_args)
            run_id = self.launch_optimization_run(self.id, organization_id, run_args)
            self.run_id = run_id
            logger.info("Started the run with ID: %s", run_id)
            return run_id
        except requests.HTTPError as error:
            try:
                content = error.response.json()
                logger.error(
                    "HTTP Error! Status code:",
                    error.response.status_code,
                    "Content:",
                    content,
                )
            except Exception:
                content = error.response.text
            raise HirundoError(
                f"Unable to start the run. Status code: {error.response.status_code} Content: {content}"
            ) from error
        except Exception as error:
            raise HirundoError(f"Unable to start the run: {error}") from error

    def clean_ids(self):
        """
        Reset `dataset_id`, `storage_config_id`, and `run_id` values on the instance to default value of `None`
        """
        self.storage_config_id = None
        self.id = None
        self.run_id = None

    @staticmethod
    def _clean_df_index(df: "pd.DataFrame") -> "pd.DataFrame":
        """
        Clean the index of a dataframe in case it has unnamed columns.

        Args:
            df (DataFrame): Dataframe to clean

        Returns:
            DataFrame: Cleaned dataframe
        """
        index_cols = sorted(
            [col for col in df.columns if col.startswith("Unnamed")], reverse=True
        )
        if len(index_cols) > 0:
            df.set_index(index_cols.pop(), inplace=True)
            df.rename_axis(index=None, columns=None, inplace=True)
            if len(index_cols) > 0:
                df.drop(columns=index_cols, inplace=True)

        return df

    @staticmethod
    def _read_csvs_to_df(data: dict):
        if data["state"] == RunStatus.SUCCESS.value:
            data["result"]["suspects"] = OptimizationDataset._clean_df_index(
                pd.read_csv(
                    StringIO(data["result"]["suspects"]),
                    dtype=CUSTOMER_INTERCHANGE_DTYPES,
                )
            )
            data["result"]["warnings_and_errors"] = OptimizationDataset._clean_df_index(
                pd.read_csv(
                    StringIO(data["result"]["warnings_and_errors"]),
                    dtype=CUSTOMER_INTERCHANGE_DTYPES,
                )
            )
        else:
            pass

    @staticmethod
    def _check_run_by_id(run_id: str, retry=0) -> Generator[dict, None, None]:
        if retry > MAX_RETRIES:
            raise HirundoError("Max retries reached")
        last_event = None
        with httpx.Client(timeout=httpx.Timeout(None, connect=5.0)) as client:
            for sse in iter_sse_retrying(
                client,
                "GET",
                f"{API_HOST}/dataset-optimization/run/{run_id}",
                headers=get_auth_headers(),
            ):
                if sse.event == "ping":
                    continue
                logger.debug(
                    "[SYNC] received event: %s with data: %s and ID: %s and retry: %s",
                    sse.event,
                    sse.data,
                    sse.id,
                    sse.retry,
                )
                last_event = json.loads(sse.data)
                if not last_event:
                    continue
                if "data" in last_event:
                    data = last_event["data"]
                else:
                    if "detail" in last_event:
                        raise HirundoError(last_event["detail"])
                    elif "reason" in last_event:
                        raise HirundoError(last_event["reason"])
                    else:
                        raise HirundoError("Unknown error")
                OptimizationDataset._read_csvs_to_df(data)
                yield data
        if not last_event or last_event["data"]["state"] == RunStatus.PENDING.value:
            OptimizationDataset._check_run_by_id(run_id, retry + 1)

    @staticmethod
    @overload
    def check_run_by_id(
        run_id: str, stop_on_manual_approval: typing.Literal[True]
    ) -> typing.Optional[DatasetOptimizationResults]: ...

    @staticmethod
    @overload
    def check_run_by_id(
        run_id: str, stop_on_manual_approval: typing.Literal[False] = False
    ) -> DatasetOptimizationResults: ...

    @staticmethod
    @overload
    def check_run_by_id(
        run_id: str, stop_on_manual_approval: bool
    ) -> typing.Optional[DatasetOptimizationResults]: ...

    @staticmethod
    def check_run_by_id(
        run_id: str, stop_on_manual_approval: bool = False
    ) -> typing.Optional[DatasetOptimizationResults]:
        """
        Check the status of a run given its ID

        Args:
            run_id: The `run_id` produced by a `run_optimization` call
            stop_on_manual_approval: If True, the function will return `None` if the run is awaiting manual approval

        Returns:
            A DatasetOptimizationResults object with the results of the optimization run

        Raises:
            HirundoError: If the maximum number of retries is reached or if the run fails
        """
        logger.debug("Checking run with ID: %s", run_id)
        with logging_redirect_tqdm():
            t = tqdm(total=100.0)
            for iteration in OptimizationDataset._check_run_by_id(run_id):
                if iteration["state"] in STATUS_TO_PROGRESS_MAP:
                    t.set_description(STATUS_TO_TEXT_MAP[iteration["state"]])
                    t.n = STATUS_TO_PROGRESS_MAP[iteration["state"]]
                    logger.debug("Setting progress to %s", t.n)
                    t.refresh()
                    if iteration["state"] in [
                        RunStatus.FAILURE.value,
                        RunStatus.REJECTED.value,
                        RunStatus.REVOKED.value,
                    ]:
                        raise HirundoError(
                            f"Optimization run failed with error: {iteration['result']}"
                        )
                    elif iteration["state"] == RunStatus.SUCCESS.value:
                        t.close()
                        return DatasetOptimizationResults(
                            suspects=iteration["result"]["suspects"],
                            warnings_and_errors=iteration["result"][
                                "warnings_and_errors"
                            ],
                        )
                    elif (
                        iteration["state"] == RunStatus.AWAITING_MANUAL_APPROVAL.value
                        and stop_on_manual_approval
                    ):
                        t.close()
                        return None
                elif iteration["state"] is None:
                    if (
                        iteration["result"]
                        and isinstance(iteration["result"], dict)
                        and iteration["result"]["result"]
                        and isinstance(iteration["result"]["result"], str)
                    ):
                        result_info = iteration["result"]["result"].split(":")
                        if len(result_info) > 1:
                            stage = result_info[0]
                            current_progress_percentage = float(
                                result_info[1].removeprefix(" ").removesuffix("% done")
                            )
                        elif len(result_info) == 1:
                            stage = result_info[0]
                            current_progress_percentage = t.n  # Keep the same progress
                        else:
                            stage = "Unknown progress state"
                            current_progress_percentage = t.n  # Keep the same progress
                        desc = (
                            "Optimization run completed. Uploading results"
                            if current_progress_percentage == 100.0
                            else stage
                        )
                        t.set_description(desc)
                        t.n = current_progress_percentage
                        logger.debug("Setting progress to %s", t.n)
                        t.refresh()
        raise HirundoError("Optimization run failed with an unknown error")

    @overload
    def check_run(
        self, stop_on_manual_approval: typing.Literal[True]
    ) -> typing.Optional[DatasetOptimizationResults]: ...

    @overload
    def check_run(
        self, stop_on_manual_approval: typing.Literal[False] = False
    ) -> DatasetOptimizationResults: ...

    def check_run(
        self, stop_on_manual_approval: bool = False
    ) -> typing.Optional[DatasetOptimizationResults]:
        """
        Check the status of the current active instance's run.

        Returns:
            A pandas DataFrame with the results of the optimization run

        """
        if not self.run_id:
            raise ValueError("No run has been started")
        return self.check_run_by_id(self.run_id, stop_on_manual_approval)

    @staticmethod
    async def acheck_run_by_id(run_id: str, retry=0) -> AsyncGenerator[dict, None]:
        """
        Async version of :func:`check_run_by_id`

        Check the status of a run given its ID.

        This generator will produce values to show progress of the run.

        Args:
            run_id: The `run_id` produced by a `run_optimization` call
            retry: A number used to track the number of retries to limit re-checks. *Do not* provide this value manually.

        Yields:
            Each event will be a dict, where:
            - `"state"` is PENDING, STARTED, RETRY, FAILURE or SUCCESS
            - `"result"` is a string describing the progress as a percentage for a PENDING state, or the error for a FAILURE state or the results for a SUCCESS state

        """
        logger.debug("Checking run with ID: %s", run_id)
        if retry > MAX_RETRIES:
            raise HirundoError("Max retries reached")
        last_event = None
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(None, connect=5.0)
        ) as client:
            async_iterator = await aiter_sse_retrying(
                client,
                "GET",
                f"{API_HOST}/dataset-optimization/run/{run_id}",
                headers=get_auth_headers(),
            )
            async for sse in async_iterator:
                if sse.event == "ping":
                    continue
                logger.debug(
                    "[ASYNC] Received event: %s with data: %s and ID: %s and retry: %s",
                    sse.event,
                    sse.data,
                    sse.id,
                    sse.retry,
                )
                last_event = json.loads(sse.data)
                yield last_event["data"]
        if not last_event or last_event["data"]["state"] == RunStatus.PENDING.value:
            OptimizationDataset.acheck_run_by_id(run_id, retry + 1)

    async def acheck_run(self) -> AsyncGenerator[dict, None]:
        """
        Async version of :func:`check_run`

        Check the status of the current active instance's run.

        This generator will produce values to show progress of the run.

        Yields:
            Each event will be a dict, where:
            - `"state"` is PENDING, STARTED, RETRY, FAILURE or SUCCESS
            - `"result"` is a string describing the progress as a percentage for a PENDING state, or the error for a FAILURE state or the results for a SUCCESS state

        """
        if not self.run_id:
            raise ValueError("No run has been started")
        async for iteration in self.acheck_run_by_id(self.run_id):
            yield iteration

    @staticmethod
    def cancel_by_id(run_id: str) -> None:
        """
        Cancel the dataset optimization run for the given `run_id`.

        Args:
            run_id: The ID of the run to cancel
        """
        if not run_id:
            raise ValueError("No run has been started")
        logger.info("Cancelling run with ID: %s", run_id)
        response = requests.delete(
            f"{API_HOST}/dataset-optimization/run/{run_id}",
            headers=get_auth_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(response)

    def cancel(self) -> None:
        """
        Cancel the current active instance's run.
        """
        if not self.run_id:
            raise ValueError("No run has been started")
        self.cancel_by_id(self.run_id)


class DataOptimizationDatasetOut(BaseModel):
    id: int

    name: str
    labeling_type: LabelingType

    storage_config: ResponseStorageConfig

    data_root_url: HirundoUrl

    classes: typing.Optional[list[str]] = None
    labeling_info: LabelingInfo

    organization_id: typing.Optional[int]
    creator_id: typing.Optional[int]
    created_at: datetime.datetime
    updated_at: datetime.datetime


class DataOptimizationRunOut(BaseModel):
    id: int
    name: str
    run_id: str
    status: RunStatus
    approved: bool
    created_at: datetime.datetime
