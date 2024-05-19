import logging
from typing import AsyncGenerator, Generator
from pydantic import BaseModel, Field
import requests
import httpx

from hirundo.enum import DatasetMetadataType, LabellingType
from hirundo.env import API_HOST
from hirundo.headers import auth_headers, json_headers
from hirundo.iter_sse_retrying import iter_sse_retrying, aiter_sse_retrying
from hirundo.storage import StorageIntegration, StorageLink

logger = logging.getLogger(__name__)


class HirundoError(Exception):
    pass


class OptimizationDataset(BaseModel):
    name: str
    labelling_type: LabellingType
    dataset_storage: StorageLink | None

    classes: list[str]
    dataset_metadata_path: str = "metadata.csv"
    dataset_metadata_type: DatasetMetadataType = DatasetMetadataType.HirundoCSV

    storage_integration_id: int | None = Field(default=None, init=False)
    dataset_id: int | None = Field(default=None, init=False)
    run_id: str | None = Field(default=None, init=False)

    @staticmethod
    def list() -> list[dict]:
        response = requests.get(
            f"{API_HOST}/dataset-optimization/dataset/", headers=auth_headers
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def delete_by_id(dataset_id: int) -> None:
        response = requests.delete(
            f"{API_HOST}/dataset-optimization/dataset/{dataset_id}",
            headers=auth_headers,
        )
        response.raise_for_status()

    def delete(self, storage_integration=True) -> None:
        if storage_integration:
            if not self.storage_integration_id:
                raise ValueError("No storage integration has been created")
            StorageIntegration.delete_by_id(self.storage_integration_id)
        if not self.dataset_id:
            raise ValueError("No dataset has been created")
        self.delete_by_id(self.dataset_id)

    def create(self) -> int:
        if (
            self.dataset_storage
            and self.dataset_storage.storage_integration
            and not self.storage_integration_id
        ):
            self.storage_integration_id = (
                self.dataset_storage.storage_integration.create()
            )
        if not self.dataset_storage:
            raise ValueError("No dataset storage has been provided")
        model_dict = self.model_dump()
        dataset_response = requests.post(
            f"{API_HOST}/dataset-optimization/dataset/",
            json={
                "dataset_storage": {
                    "storage_integration_id": self.storage_integration_id,
                    "path": self.dataset_storage.path,
                },
                **{
                    k: model_dict[k]
                    for k in set(list(model_dict.keys())) - set(["dataset_storage"])
                },
            },
            headers={
                **json_headers,
                **auth_headers,
            },
        )
        dataset_response.raise_for_status()
        self.dataset_id = dataset_response.json()["id"]
        if not self.dataset_id:
            raise HirundoError("Failed to create the dataset")
        return self.dataset_id

    @staticmethod
    def launch_optimization_run(dataset_id: int):
        run_response = requests.post(
            f"{API_HOST}/dataset-optimization/run/{dataset_id}",
            headers=auth_headers,
        )
        run_response.raise_for_status()
        return run_response.json()["run_id"]

    def run_optimization(self) -> str:
        """
        Run the dataset optimization process
        Returns an ID of the run and stores the run on the dataset instance
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
        self.storage_integration_id = None
        self.dataset_id = None
        self.run_id = None

    @staticmethod
    def check_run_by_id(run_id: str) -> Generator[str, None, None]:
        """
        Check the status of a run

        This generator will produce values to show progress of the run.
        Each event will be a dict, where:
        - `"state"` is PENDING, STARTED, RETRY, FAILURE or SUCCESS
        - `"result"` is a string describing the progress as a percentage for a PENDING state, or the error for a FAILURE state or the results for a SUCCESS state

        """
        with httpx.Client(timeout=httpx.Timeout(5.0, read=None)) as client:
            for sse in iter_sse_retrying(
                client, "GET", f"{API_HOST}/dataset-optimization/run/{run_id}"
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
                yield sse.data

    def check_run(self) -> Generator[str, None, None]:
        """
        Check the status of the instance's run

        This generator will produce values to show progress of the run.
        Each event will be a dict, where:
        - `"state"` is PENDING, STARTED, RETRY, FAILURE or SUCCESS
        - `"result"` is a string describing the progress as a percentage for a PENDING state, or the error for a FAILURE state or the results for a SUCCESS state

        """
        if not self.run_id:
            raise ValueError("No run has been started")
        return self.check_run_by_id(self.run_id)

    @staticmethod
    async def acheck_run_by_id(run_id: str) -> AsyncGenerator[str, None]:
        """
        Async version of :func:`check_run_by_id`
        """
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, read=None)) as client:
            async_iterator = await aiter_sse_retrying(
                client, "GET", f"{API_HOST}/dataset-optimization/run/{run_id}"
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
                yield sse.data

    async def acheck_run(self) -> AsyncGenerator[str, None]:
        """
        Async version of check_run

        """
        if not self.run_id:
            raise ValueError("No run has been started")
        async for iteration in self.acheck_run_by_id(self.run_id):
            yield iteration
