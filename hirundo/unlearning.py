import datetime
import json
import typing
from typing import Annotated

import httpx
import requests
from pydantic import BaseModel, Field

from hirundo._env import API_HOST
from hirundo._headers import get_headers
from hirundo._http import raise_for_status_with_reason
from hirundo._iter_sse_retrying import aiter_sse_retrying, iter_sse_retrying
from hirundo._timeouts import MODIFY_TIMEOUT, READ_TIMEOUT
from hirundo.logger import get_logger

logger = get_logger(__name__)


class PyTorchRawPthModel(BaseModel):
    type: typing.Literal["pytorch_raw_pth"] = Field(
        default="pytorch_raw_pth", frozen=True
    )
    code_url: str
    raw_pth_url: str


class TorchVisionModel(BaseModel):
    type: typing.Literal["torchvision"] = Field(default="torchvision", frozen=True)
    model_name: str
    safetensors_weights_url: str


CvModelSource = Annotated[
    typing.Union[PyTorchRawPthModel, TorchVisionModel],
    Field(discriminator="type"),
]


class CreateMLModel(BaseModel):
    storage_config_id: int
    class_mapping_url: str
    data_root_url: str
    model_name: str
    model_source: CvModelSource
    organization_id: typing.Optional[int] = None
    replace_if_exists: bool = False
    archive_existing_runs: bool = True


class ModifyMLModel(BaseModel):
    storage_config_id: typing.Optional[int] = None
    class_mapping_url: typing.Optional[str] = None
    data_root_url: typing.Optional[str] = None
    organization_id: typing.Optional[int] = None
    creator_id: typing.Optional[int] = None
    model_name: typing.Optional[str] = None
    model_source: typing.Optional[CvModelSource] = None
    archive_existing_runs: bool = True


class OutputMLModel(BaseModel):
    id: int
    storage_config_id: int
    class_mapping_url: str
    data_root_url: str
    organization_id: int
    creator_id: int
    creator_name: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    model_name: str
    model_source: CvModelSource


class MLModel(BaseModel):
    id: typing.Optional[int] = None
    storage_config_id: int
    class_mapping_url: str
    data_root_url: str
    organization_id: typing.Optional[int] = None
    model_name: str
    model_source: CvModelSource
    replace_if_exists: bool = False
    archive_existing_runs: bool = True

    def create(self, replace_if_exists: bool = False) -> int:
        payload = {
            **self.model_dump(mode="json"),
            "replace_if_exists": replace_if_exists,
        }
        response = requests.post(
            f"{API_HOST}/unlearning/ml-model/",
            json=payload,
            headers=get_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(response)
        self.id = int(response.json()["id"])
        return typing.cast("int", self.id)

    @staticmethod
    def get_by_id(model_id: int) -> "OutputMLModel":
        response = requests.get(
            f"{API_HOST}/unlearning/ml-model/{model_id}",
            headers=get_headers(),
            timeout=READ_TIMEOUT,
        )
        raise_for_status_with_reason(response)
        return OutputMLModel(**response.json())

    @staticmethod
    def get_by_name(model_name: str, organization_id: typing.Optional[int] = None) -> "OutputMLModel":
        response = requests.get(
            f"{API_HOST}/unlearning/ml-model/by-name/{model_name}",
            params={"model_organization_id": organization_id},
            headers=get_headers(),
            timeout=READ_TIMEOUT,
        )
        raise_for_status_with_reason(response)
        return OutputMLModel(**response.json())

    @staticmethod
    def list(organization_id: typing.Optional[int] = None) -> list["OutputMLModel"]:
        response = requests.get(
            f"{API_HOST}/unlearning/ml-model/",
            params={"model_organization_id": organization_id},
            headers=get_headers(),
            timeout=READ_TIMEOUT,
        )
        raise_for_status_with_reason(response)
        return [OutputMLModel(**m) for m in response.json()]

    def update(self) -> None:
        if self.id is None:
            raise ValueError("Model must be created before update")
        response = requests.put(
            f"{API_HOST}/unlearning/ml-model/{self.id}",
            json=self.model_dump(mode="json"),
            headers=get_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(response)

    @staticmethod
    def delete_by_id(model_id: int) -> None:
        response = requests.delete(
            f"{API_HOST}/unlearning/ml-model/{model_id}",
            headers=get_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(response)

    def delete(self) -> None:
        if self.id is None:
            raise ValueError("Model must be created before delete")
        self.delete_by_id(self.id)


class UnlearningCvModelRun:
    """Manage CV unlearning runs."""

    @staticmethod
    def launch(model_id: int, run_info: dict) -> str:
        response = requests.post(
            f"{API_HOST}/unlearning/run/{model_id}",
            json=run_info,
            headers=get_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(response)
        return typing.cast("str", response.json()["run_id"])

    @staticmethod
    def cancel(hir_run_id: str) -> None:
        response = requests.patch(
            f"{API_HOST}/unlearning/run/cancel/{hir_run_id}",
            headers=get_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(response)

    @staticmethod
    def archive(hir_run_id: str) -> None:
        response = requests.patch(
            f"{API_HOST}/unlearning/run/archive/{hir_run_id}",
            headers=get_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(response)

    @staticmethod
    def restore(hir_run_id: str) -> None:
        response = requests.patch(
            f"{API_HOST}/unlearning/run/restore/{hir_run_id}",
            headers=get_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(response)

    @staticmethod
    def approve(hir_run_id: str) -> None:
        response = requests.post(
            f"{API_HOST}/unlearning/run/{hir_run_id}/approve",
            headers=get_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(response)

    @staticmethod
    def list(
        organization_id: typing.Optional[int] = None,
        archived: bool = False,
    ) -> list[dict]:
        response = requests.get(
            f"{API_HOST}/unlearning/run/list",
            params={
                "unlearning_organization_id": organization_id,
                "archived": archived,
            },
            headers=get_headers(),
            timeout=READ_TIMEOUT,
        )
        raise_for_status_with_reason(response)
        return typing.cast("list[dict]", response.json())

    @staticmethod
    def stream_results(hir_run_id: str) -> typing.Generator[dict, None, None]:
        iterator = iter_sse_retrying(
            requests,
            "GET",
            f"{API_HOST}/unlearning/run/{hir_run_id}",
            headers=get_headers(),
        )
        for sse in iterator:
            if sse.event == "ping":
                continue
            yield json.loads(sse.data)["data"]

    @staticmethod
    async def astream_results(
        hir_run_id: str,
    ) -> typing.AsyncGenerator[dict, None]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=5.0)) as client:
            async_iterator = await aiter_sse_retrying(
                client,
                "GET",
                f"{API_HOST}/unlearning/run/{hir_run_id}",
                headers=get_headers(),
            )
            async for sse in async_iterator:
                if sse.event == "ping":
                    continue
                yield json.loads(sse.data)["data"]

