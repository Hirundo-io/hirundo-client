import asyncio
import time
from collections.abc import AsyncGenerator, Generator
from typing import Union

import httpx
from httpx_sse import ServerSentEvent, aconnect_sse, connect_sse
from stamina import retry


# Credit: https://github.com/florimondmanca/httpx-sse/blob/master/README.md#handling-reconnections
def iter_sse_retrying(
    client: httpx.Client,
    method: str,
    url: str,
    headers: Union[dict[str, str], None] = None,
) -> Generator[ServerSentEvent, None, None]:
    if headers is None:
        headers = {}
    last_event_id = ""
    reconnection_delay = 0.0

    # `stamina` will apply jitter and exponential backoff on top of
    # the `retry` reconnection delay sent by the server.
    @retry(on=httpx.ReadError)
    def _iter_sse():
        nonlocal last_event_id, reconnection_delay

        time.sleep(reconnection_delay)

        connect_headers = {
            **headers,
            "Accept": "text/event-stream",
            "X-Accel-Buffering": "no",
        }

        if last_event_id:
            connect_headers["Last-Event-ID"] = last_event_id

        with connect_sse(client, method, url, headers=connect_headers) as event_source:
            for sse in event_source.iter_sse():
                last_event_id = sse.id

                if sse.retry is not None:
                    reconnection_delay = sse.retry / 1000

                yield sse

    return _iter_sse()


async def aiter_sse_retrying(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: dict[str, str],
) -> AsyncGenerator[ServerSentEvent, None]:
    last_event_id = ""
    reconnection_delay = 0.0

    # `stamina` will apply jitter and exponential backoff on top of
    # the `retry` reconnection delay sent by the server.
    @retry(on=httpx.ReadError)
    async def _iter_sse() -> AsyncGenerator[ServerSentEvent, None]:
        nonlocal last_event_id, reconnection_delay

        await asyncio.sleep(reconnection_delay)

        connect_headers = {**headers, "Accept": "text/event-stream"}

        if last_event_id:
            connect_headers["Last-Event-ID"] = last_event_id

        async with aconnect_sse(
            client, method, url, headers=connect_headers
        ) as event_source:
            async for sse in event_source.aiter_sse():
                last_event_id = sse.id

                if sse.retry is not None:
                    reconnection_delay = sse.retry / 1000

                yield sse

    return _iter_sse()