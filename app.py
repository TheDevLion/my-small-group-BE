import threading
import time

from flask import Flask, jsonify, request
from flask_cors import CORS

from config import (
    CORS_ORIGINS,
    HYGRAPH_ADMIN_TOKEN,
    RATE_LIMIT_MAX_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    SESSION_SECRET_KEY,
)
from routes.auth import auth_bp
from routes.docs import docs_bp
from routes.event_photos import event_photos_bp
from routes.group import group_bp

_rate_lock = threading.Lock()
_rate_state = {}


def _get_client_ip():
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _check_rate_limit(ip):
    now = time.time()
    with _rate_lock:
        record = _rate_state.get(ip)
        if not record or now - record["start"] >= RATE_LIMIT_WINDOW_SECONDS:
            record = {"start": now, "count": 0}
            _rate_state[ip] = record
        if record["count"] >= RATE_LIMIT_MAX_REQUESTS:
            retry_after = int(RATE_LIMIT_WINDOW_SECONDS - (now - record["start"]))
            return True, max(retry_after, 0)
        record["count"] += 1
        return False, None


def create_app():
    if not HYGRAPH_ADMIN_TOKEN:
        raise RuntimeError("Missing HYGRAPH_ADMIN_TOKEN environment variable.")
    if not SESSION_SECRET_KEY:
        raise RuntimeError("Missing SESSION_SECRET_KEY environment variable.")

    app = Flask(__name__)
    CORS(app, supports_credentials=True, origins=CORS_ORIGINS)
    app.config["CORS_HEADERS"] = "Content-Type, Authorization"

    @app.before_request
    def apply_rate_limit():
        ip = _get_client_ip()
        limited, retry_after = _check_rate_limit(ip)
        if limited:
            response = jsonify(
                {
                    "error": "rate_limit",
                    "message": "Too many requests. Try again later.",
                }
            )
            response.status_code = 429
            response.headers["Retry-After"] = str(retry_after)
            return response

    app.register_blueprint(auth_bp)
    app.register_blueprint(docs_bp)
    app.register_blueprint(group_bp)
    app.register_blueprint(event_photos_bp)

    return app
