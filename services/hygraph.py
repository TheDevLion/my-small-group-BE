import requests

from config import HYGRAPH_ADMIN_TOKEN, HYGRAPH_API_URL


def graphcms_request(bearer_token, query, variables=None):
    payload = {"query": query}
    if variables is not None:
        payload["variables"] = variables

    try:
        r = requests.post(
            HYGRAPH_API_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "authorization": f"Bearer {bearer_token}",
            },
            timeout=15,
        )
        if not r.ok:
            return None
        data = r.json()
        if data.get("errors"):
            return None
        return data.get("data")
    except Exception:
        return None


def _fetch_tokens():
    if not HYGRAPH_ADMIN_TOKEN:
        return None

    payload = {"query": "query MyQuery { tokens(){ password tokenDescription bearerToken } }"}
    try:
        r = requests.post(
            HYGRAPH_API_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "authorization": f"Bearer {HYGRAPH_ADMIN_TOKEN}",
            },
            timeout=15,
        )
        if not r.ok:
            return None
        return r.json().get("data", {}).get("tokens", [])
    except Exception:
        return None


def get_bearer_token(user_password):
    tokens = _fetch_tokens()
    if not tokens:
        return None

    for entry in tokens:
        if entry.get("password") == user_password:
            return entry.get("bearerToken"), entry.get("tokenDescription")
    return None


def get_bearer_token_by_group(group_id):
    tokens = _fetch_tokens()
    if not tokens:
        return None

    for entry in tokens:
        if entry.get("tokenDescription") == group_id:
            return entry.get("bearerToken")
    return None


def publish_group(bearer_token, group_id):
    mutation = """
        mutation PublishGroup($id: ID!) {
            publishGroup(to: PUBLISHED, where: {id: $id}) { id }
        }
    """
    graphcms_request(bearer_token, mutation, {"id": group_id})


def publish_asset(bearer_token, asset_id):
    mutation = """
        mutation PublishAsset($id: ID!) {
            publishAsset(to: PUBLISHED, where: {id: $id}) { id }
        }
    """
    graphcms_request(bearer_token, mutation, {"id": asset_id})


def publish_event_photo(bearer_token, event_photo_id):
    mutation = """
        mutation PublishEventPhoto($id: ID!) {
            publishEventPhoto(to: PUBLISHED, where: {id: $id}) { id }
        }
    """
    graphcms_request(bearer_token, mutation, {"id": event_photo_id})


def upload_asset(bearer_token, file_storage):
    try:
        upload_response = requests.post(
            f"{HYGRAPH_API_URL}/upload",
            headers={
                "authorization": f"Bearer {bearer_token}",
            },
            files={
                "fileUpload": (
                    file_storage.filename,
                    file_storage.stream,
                    file_storage.mimetype,
                )
            },
            timeout=30,
        )
    except Exception:
        return None

    if not upload_response.ok:
        return None

    upload_data = upload_response.json()
    return upload_data
