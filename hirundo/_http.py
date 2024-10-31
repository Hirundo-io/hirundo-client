from requests import Response

import hirundo.logger

logger = hirundo.logger.get_logger(__name__)

MINIMUM_CLIENT_SERVER_ERROR_CODE = 400


def raise_for_status_with_reason(response: Response):
    try:
        if response.status_code >= MINIMUM_CLIENT_SERVER_ERROR_CODE:
            response.reason = response.json().get("reason", None)
            if response.reason is None:
                response.reason = response.json().get("detail", None)
    except Exception as e:
        logger.debug("Could not parse response as JSON: %s", e)

    response.raise_for_status()
