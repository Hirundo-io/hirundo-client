import json
import logging
from collections.abc import AsyncGenerator, Generator
from typing import Union

import httpx
import requests
from pydantic import BaseModel, Field, model_validator

from hirundo.enum import DatasetMetadataType, LabellingType
from hirundo.env import API_HOST
from hirundo.headers import auth_headers, json_headers
from hirundo.iter_sse_retrying import aiter_sse_retrying, iter_sse_retrying
from hirundo.storage import StorageIntegration, StorageLink

logger = logging.getLogger(__name__)

READ_TIMEOUT = 5.0
MODIFY_TIMEOUT = 10.0


class HirundoError(Exception):
    pass


MAX_RETRIES = 200  # Max 200 retries for HTTP SSE connection


class OptimizationDataset(BaseModel):
    name: str
    labelling_type: LabellingType
    dataset_storage: Union[StorageLink, None]

    classes: list[str]
    dataset_metadata_path: str = "metadata.csv"
    """
    The path to the dataset metadata file within storage integration, e.g. S3 Bucket / GCP Bucket / Azure Blob storage / Git repo.
    Note: This path will be prefixed with the `StorageLink`'s `path`
    """
    dataset_metadata_type: DatasetMetadataType = DatasetMetadataType.HirundoCSV

    storage_integration_id: Union[int, None] = Field(default=None, init=False)
    dataset_id: Union[int, None] = Field(default=None, init=False)
    run_id: Union[str, None] = Field(default=None, init=False)

    @model_validator(mode="after")
    def validate_repo(self):
        if self.dataset_storage is None and self.storage_integration_id is None:
            raise ValueError("No dataset storage has been provided")
        return self

    @staticmethod
    def list(organization_id: Union[int, None] = None) -> list[dict]:
        """
        Lists all the `OptimizationDataset` instances created by user's default organization
        or the `organization_id` passed
        Note: The return type is `list[dict]` and not `list[OptimizationDataset]`
        """
        response = requests.get(
            f"{API_HOST}/dataset-optimization/dataset/",
            params={"dataset_organization_id": organization_id},
            headers=auth_headers,
            timeout=READ_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def delete_by_id(dataset_id: int) -> None:
        """
        Deletes a `OptimizationDataset` instance from the server by its ID
        """
        response = requests.delete(
            f"{API_HOST}/dataset-optimization/dataset/{dataset_id}",
            headers=auth_headers,
            timeout=MODIFY_TIMEOUT,
        )
        response.raise_for_status()

    def delete(self, storage_integration=True) -> None:
        """
        Deletes the active `OptimizationDataset` instance from the server.
        It can only be used on a `OptimizationDataset` instance that has been created.

        storage_integration: If True, the `OptimizationDataset`'s `StorageIntegration` will also be deleted

        Note: If `storage_integration` is not set to `False` then the `storage_integration_id` must be set
        This can either be set manually or by creating the `StorageIntegration` instance via the `OptimizationDataset`'s
        `create` method
        """
        if storage_integration:
            if not self.storage_integration_id:
                raise ValueError("No storage integration has been created")
            StorageIntegration.delete_by_id(self.storage_integration_id)
        if not self.dataset_id:
            raise ValueError("No dataset has been created")
        self.delete_by_id(self.dataset_id)

    def create(self) -> int:
        """
        Create a `OptimizationDataset` instance on the server.
        If `storage_integration_id` is not set, it will be created.
        """
        if not self.dataset_storage:
            raise ValueError("No dataset storage has been provided")
        if (
            self.dataset_storage
            and self.dataset_storage.storage_integration
            and not self.storage_integration_id
        ):
            self.storage_integration_id = (
                self.dataset_storage.storage_integration.create()
            )
        model_dict = self.model_dump()
        # ⬆️ Get dict of model fields from Pydantic model instance
        dataset_response = requests.post(
            f"{API_HOST}/dataset-optimization/dataset/",
            json={
                "dataset_storage": {
                    "storage_integration_id": self.storage_integration_id,
                    "path": self.dataset_storage.path,
                },
                **{k: model_dict[k] for k in model_dict.keys() - {"dataset_storage"}},
            },
            headers={
                **json_headers,
                **auth_headers,
            },
            timeout=MODIFY_TIMEOUT,
        )
        dataset_response.raise_for_status()
        self.dataset_id = dataset_response.json()["id"]
        if not self.dataset_id:
            raise HirundoError("Failed to create the dataset")
        return self.dataset_id

    @staticmethod
    def launch_optimization_run(dataset_id: int) -> str:
        """
        Run the dataset optimization process on the server using the dataset with the given ID
        i.e. `dataset_id`
        Returns the ID of the run (`run_id`)
        """
        run_response = requests.post(
            f"{API_HOST}/dataset-optimization/run/{dataset_id}",
            headers=auth_headers,
            timeout=MODIFY_TIMEOUT,
        )
        run_response.raise_for_status()
        return run_response.json()["run_id"]

    def run_optimization(self) -> str:
        """
        If the dataset was not created on the server yet, it is created.
        Run the dataset optimization process on the server using the active `OptimizationDataset` instance
        Returns an ID of the run (`run_id`) and stores that `run_id` on the instance
        """
        try:
            if not self.dataset_id:
                self.dataset_id = self.create()
            run_id = self.launch_optimization_run(self.dataset_id)
            self.run_id = run_id
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
                f"Failed to start the run. Status code: {error.response.status_code} Content: {content}"
            ) from error
        except Exception as error:
            raise HirundoError(f"Failed to start the run: {error}") from error

    def clean_ids(self):
        """
        Reset `dataset_id`, `storage_integration_id`, and `run_id` values on the instance to default value of `None`
        """
        self.storage_integration_id = None
        self.dataset_id = None
        self.run_id = None

    @staticmethod
    def check_run_by_id(run_id: str, retry=0) -> Generator[dict, None, None]:
        """
        Check the status of a run given its ID

        This generator will produce values to show progress of the run.
        Each event will be a dict, where:
        - `"state"` is PENDING, STARTED, RETRY, FAILURE or SUCCESS
        - `"result"` is a string describing the progress as a percentage for a PENDING state, or the error for a FAILURE state or the results for a SUCCESS state

        """
        if retry > MAX_RETRIES:
            raise HirundoError("Max retries reached")
        last_event = None
        with httpx.Client(timeout=httpx.Timeout(None, connect=5.0)) as client:
            for sse in iter_sse_retrying(
                client,
                "GET",
                f"{API_HOST}/dataset-optimization/run/{run_id}",
                headers=auth_headers,
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
                yield last_event["data"]
        if not last_event or last_event["data"]["state"] == "PENDING":
            OptimizationDataset.check_run_by_id(run_id, retry + 1)

    def check_run(self) -> Generator[dict, None, None]:
        """
        Check the status of the current active instance's run

        This generator will produce values to show progress of the run.
        Each event will be a dict, where:
        - `"state"` is PENDING, STARTED, RETRY, FAILURE or SUCCESS
        - `"result"` is a string describing the progress as a percentage for a PENDING state, or the error for a FAILURE state or the results for a SUCCESS state

        """
        if not self.run_id:
            raise ValueError("No run has been started")
        return self.check_run_by_id(self.run_id)

    @staticmethod
    async def acheck_run_by_id(run_id: str, retry=0) -> AsyncGenerator[dict, None]:
        """
        Async version of :func:`check_run_by_id`

        Check the status of a run given its ID

        This generator will produce values to show progress of the run.
        Each event will be a dict, where:
        - `"state"` is PENDING, STARTED, RETRY, FAILURE or SUCCESS
        - `"result"` is a string describing the progress as a percentage for a PENDING state, or the error for a FAILURE state or the results for a SUCCESS state

        """
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
                headers=auth_headers,
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
        if not last_event or last_event["data"]["state"] == "PENDING":
            OptimizationDataset.acheck_run_by_id(run_id, retry + 1)

    async def acheck_run(self) -> AsyncGenerator[dict, None]:
        """
        Async version of :func:`check_run`

        Check the status of the current active instance's run

        This generator will produce values to show progress of the run.
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
        Cancel the dataset optimization run for the given `run_id`
        """
        if not run_id:
            raise ValueError("No run has been started")
        response = requests.delete(
            f"{API_HOST}/dataset-optimization/run/{run_id}",
            headers=auth_headers,
            timeout=MODIFY_TIMEOUT,
        )
        response.raise_for_status()

    def cancel(self) -> None:
        """
        Cancel the current active instance's run
        """
        if not self.run_id:
            raise ValueError("No run has been started")
        self.cancel_by_id(self.run_id)
