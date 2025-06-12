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


class HuggingFaceTransformersModel(BaseModel):
    type: typing.Literal["huggingface_transformers"] = Field(
        default="huggingface_transformers", frozen=True
    )
    model_name: str
    token: typing.Optional[str] = None


class LocalTransformersModel(BaseModel):
    type: typing.Literal["local_transformers"] = Field(
        default="local_transformers", frozen=True
    )
    local_path: str


LlmModelSource = Annotated[
    typing.Union[HuggingFaceTransformersModel, LocalTransformersModel],
    Field(discriminator="type"),
]


class CreateLlm(BaseModel):
    organization_id: typing.Optional[int] = None
    model_name: str
    model_source: LlmModelSource
    replace_if_exists: bool = False
    archive_existing_runs: bool = True


class ModifyLlm(BaseModel):
    organization_id: typing.Optional[int] = None
    creator_id: typing.Optional[int] = None
    model_name: typing.Optional[str] = None
    model_source: typing.Optional[LlmModelSource] = None
    archive_existing_runs: bool = True


class OutputLlm(BaseModel):
    id: int
    organization_id: int
    creator_id: int
    creator_name: str
    created_at: str
    updated_at: str
    model_name: str
    model_source: LlmModelSource


class LlmModel(BaseModel):
    id: typing.Optional[int] = None
    organization_id: typing.Optional[int] = None
    model_name: str
    model_source: LlmModelSource
    replace_if_exists: bool = False
    archive_existing_runs: bool = True

    def create(self, replace_if_exists: bool = False) -> int:
        payload = {
            **self.model_dump(mode="json"),
            "replace_if_exists": replace_if_exists,
        }
        response = requests.post(
            f"{API_HOST}/unlearning-llm-behavior/llm/",
            json=payload,
            headers=get_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(response)
        self.id = int(response.json()["id"])
        return typing.cast("int", self.id)

    @staticmethod
    def get_by_id(llm_model_id: int) -> "OutputLlm":
        response = requests.get(
            f"{API_HOST}/unlearning-llm-behavior/llm/{llm_model_id}",
            headers=get_headers(),
            timeout=READ_TIMEOUT,
        )
        raise_for_status_with_reason(response)
        return OutputLlm(**response.json())

    @staticmethod
    def get_by_name(model_name: str, organization_id: typing.Optional[int] = None) -> "OutputLlm":
        response = requests.get(
            f"{API_HOST}/unlearning-llm-behavior/llm/by-name/{model_name}",
            params={"model_organization_id": organization_id},
            headers=get_headers(),
            timeout=READ_TIMEOUT,
        )
        raise_for_status_with_reason(response)
        return OutputLlm(**response.json())

    @staticmethod
    def list(organization_id: typing.Optional[int] = None) -> list["OutputLlm"]:
        response = requests.get(
            f"{API_HOST}/unlearning-llm-behavior/llm/",
            params={"model_organization_id": organization_id},
            headers=get_headers(),
            timeout=READ_TIMEOUT,
        )
        raise_for_status_with_reason(response)
        return [OutputLlm(**m) for m in response.json()]

    def update(self) -> None:
        if self.id is None:
            raise ValueError("Model must be created before update")
        response = requests.put(
            f"{API_HOST}/unlearning-llm-behavior/llm/{self.id}",
            json=self.model_dump(mode="json"),
            headers=get_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(response)

    @staticmethod
    def delete_by_id(llm_model_id: int) -> None:
        response = requests.delete(
            f"{API_HOST}/unlearning-llm-behavior/llm/{llm_model_id}",
            headers=get_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(response)

    def delete(self) -> None:
        if self.id is None:
            raise ValueError("Model must be created before delete")
        self.delete_by_id(self.id)


class LlmUnlearningRun:
    """Manage LLM behavior unlearning runs."""

    @staticmethod
    def launch(model_id: int, run_info: dict) -> str:
        response = requests.post(
            f"{API_HOST}/unlearning-llm-behavior/run/{model_id}",
            json=run_info,
            headers=get_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(response)
        return typing.cast("str", response.json()["run_id"])

    @staticmethod
    def cancel(hir_run_id: str) -> None:
        response = requests.patch(
            f"{API_HOST}/unlearning-llm-behavior/run/cancel/{hir_run_id}",
            headers=get_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(response)

    @staticmethod
    def archive(hir_run_id: str) -> None:
        response = requests.patch(
            f"{API_HOST}/unlearning-llm-behavior/run/archive/{hir_run_id}",
            headers=get_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(response)

    @staticmethod
    def restore(hir_run_id: str) -> None:
        response = requests.patch(
            f"{API_HOST}/unlearning-llm-behavior/run/restore/{hir_run_id}",
            headers=get_headers(),
            timeout=MODIFY_TIMEOUT,
        )
        raise_for_status_with_reason(response)

    @staticmethod
    def approve(hir_run_id: str) -> None:
        response = requests.post(
            f"{API_HOST}/unlearning-llm-behavior/run/{hir_run_id}/approve",
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
            f"{API_HOST}/unlearning-llm-behavior/run/list",
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
            f"{API_HOST}/unlearning-llm-behavior/run/{hir_run_id}",
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
                f"{API_HOST}/unlearning-llm-behavior/run/{hir_run_id}",
                headers=get_headers(),
            )
            async for sse in async_iterator:
                if sse.event == "ping":
                    continue
                yield json.loads(sse.data)["data"]

