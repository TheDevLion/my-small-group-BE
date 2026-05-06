from flask import request
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from config import (
    COOKIE_SAMESITE,
    COOKIE_SECURE,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SALT,
    SESSION_SECRET_KEY,
    SESSION_TTL_SECONDS,
)
from services.hygraph import get_bearer_token_by_group


def _serializer():
    return URLSafeTimedSerializer(SESSION_SECRET_KEY, salt=SESSION_COOKIE_SALT)


def _extract_group_id(session_token):
    if not session_token:
        return None

    try:
        data = _serializer().loads(session_token, max_age=SESSION_TTL_SECONDS)
    except (BadSignature, SignatureExpired):
        return None

    group_id = data.get("group_id") if isinstance(data, dict) else None
    if not group_id:
        return None

    return group_id


def _get_authorization_token():
    header_value = request.headers.get("Authorization", "").strip()
    if not header_value:
        return None

    scheme, _, token = header_value.partition(" ")
    if scheme.lower() != "bearer":
        return None

    token = token.strip()
    if not token:
        return None

    return token


def _get_group_id_from_authorization():
    token = _get_authorization_token()
    if not token:
        return None

    return _extract_group_id(token)


def _get_group_id_from_cookie():
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    return _extract_group_id(session_token)


def require_session():
    group_id = _get_group_id_from_authorization()
    if not group_id:
        group_id = _get_group_id_from_cookie()

    if not group_id:
        return None, ({"error": "unauthorized"}, 401)

    bearer_token = get_bearer_token_by_group(group_id)
    if not bearer_token:
        return None, ({"error": "unauthorized"}, 401)

    return (None, {"group_id": group_id, "bearer_token": bearer_token}), None


def start_session(group_id):
    return _serializer().dumps({"group_id": group_id})


def set_session_cookie(response, session_token):
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )


def clear_session_cookie(response):
    response.set_cookie(SESSION_COOKIE_NAME, "", expires=0)
