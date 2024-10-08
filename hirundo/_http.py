from requests import Response

import hirundo.logger

logger = hirundo.logger.get_logger(__name__)


def raise_for_status_with_reason(response: Response):
    try:
        if response.status_code >= 400:
            response.reason = response.json().get("reason", None)
            if response.reason is None:
                response.reason = response.json().get("detail", None)
    except Exception as e:
        logger.debug("Failed to parse response as JSON: %s", e)

    response.raise_for_status()
