from hirundo.env import API_KEY


json_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}
auth_headers = {
    "Authorization": f"Bearer {API_KEY}",
}
