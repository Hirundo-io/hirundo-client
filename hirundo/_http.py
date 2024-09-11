from requests import Response

import hirundo.logger

logger = hirundo.logger.get_logger(__name__)


def raise_for_status_with_reason(response: Response):
    try:
        response.reason = response.json().get("reason", None)
    except Exception as e:
        logger.debug("Failed to parse response as JSON: %s", e)

    response.raise_for_status()
