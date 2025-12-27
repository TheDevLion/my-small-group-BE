import secrets
import time

SESSION_STORE = {}


def _now():
    return int(time.time())


def prune_sessions():
    now = _now()
    expired = [sid for sid, sess in SESSION_STORE.items() if sess["expires_at"] <= now]
    for sid in expired:
        SESSION_STORE.pop(sid, None)


def create_session(group_id, bearer_token, ttl_seconds):
    prune_sessions()
    session_id = secrets.token_urlsafe(32)
    SESSION_STORE[session_id] = {
        "group_id": group_id,
        "bearer_token": bearer_token,
        "expires_at": _now() + ttl_seconds,
    }
    return session_id


def get_session(session_id):
    if not session_id:
        return None
    prune_sessions()
    session = SESSION_STORE.get(session_id)
    if not session:
        return None
    if session["expires_at"] <= _now():
        SESSION_STORE.pop(session_id, None)
        return None
    return session


def clear_session(session_id):
    if session_id:
        SESSION_STORE.pop(session_id, None)
