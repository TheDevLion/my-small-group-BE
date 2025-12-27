import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_HYGRAPH_API_URL = "https://api-sa-east-1.hygraph.com/v2/clrcfb59c1wlg01w791sij1fq/master"


def _parse_cors_origins():
    raw = os.getenv("CORS_ORIGINS", "")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not origins:
        origins = ["http://localhost:4200"]
    return origins


def _normalize_samesite(value):
    if not value:
        return "Lax"
    cleaned = value.strip()
    lowered = cleaned.lower()
    if lowered == "none":
        return "None"
    if lowered == "lax":
        return "Lax"
    if lowered == "strict":
        return "Strict"
    return cleaned


HYGRAPH_API_URL = os.getenv("HYGRAPH_API_URL", DEFAULT_HYGRAPH_API_URL)
HYGRAPH_ADMIN_TOKEN = os.getenv("HYGRAPH_ADMIN_TOKEN")
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY") or os.getenv("SECRET_KEY")
SESSION_COOKIE_SALT = os.getenv("SESSION_COOKIE_SALT", "msg_session")

CORS_ORIGINS = _parse_cors_origins()

SESSION_COOKIE_NAME = "msg_session"
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "28800"))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = _normalize_samesite(os.getenv("COOKIE_SAMESITE", "Lax"))
