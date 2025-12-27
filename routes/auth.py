from flask import Blueprint, request, make_response
from flask_cors import cross_origin

from services.hygraph import get_bearer_token
from services.session_auth import (
    clear_session_cookie,
    set_session_cookie,
    start_session,
)


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
@cross_origin(supports_credentials=True)
def login():
    data = request.get_json(silent=True) or {}
    password = data.get("payload")
    if not password:
        return {"error": "missing_password"}, 400

    auth_token = get_bearer_token(password)
    if not auth_token:
        return {"error": "wrong_password"}, 401

    _, group_id = auth_token
    session_token = start_session(group_id)
    response = make_response({"groupID": group_id})
    set_session_cookie(response, session_token)
    return response


@auth_bp.route("/logout", methods=["POST"])
@cross_origin(supports_credentials=True)
def logout():
    response = make_response({"ok": True})
    clear_session_cookie(response)
    return response


@auth_bp.route("/info", methods=["POST"])
@cross_origin(supports_credentials=True)
def info_deprecated():
    return {"error": "deprecated", "message": "Use /login instead."}, 410
