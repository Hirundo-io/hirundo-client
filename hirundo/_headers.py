from hirundo._env import API_KEY, check_api_key

json_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def get_auth_headers():
    check_api_key()
    return {
        "Authorization": f"Bearer {API_KEY}",
    }
