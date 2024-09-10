from requests import Response


def raise_for_status_with_reason(response: Response):
    try:
        response.reason = response.json().get("reason", None)
    except Exception:
        response.reason = None

    response.raise_for_status()
