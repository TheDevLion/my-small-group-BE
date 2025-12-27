from flask import Blueprint, request
from flask_cors import cross_origin

from services.hygraph import graphcms_request, publish_group
from services.session_auth import require_session


group_bp = Blueprint("group", __name__)


@group_bp.route("/group", methods=["GET"])
@cross_origin(supports_credentials=True)
def get_group():
    session, err = require_session()
    if err:
        return err
    _, session_data = session

    query = """
        query GetGroup($id: ID!) {
            group(where: {id: $id}) {
                id
                name
                participants
                events
                template
            }
        }
    """

    data = graphcms_request(
        session_data["bearer_token"],
        query,
        {"id": session_data["group_id"]},
    )
    if not data or not data.get("group"):
        return {"error": "api_unavailable"}, 502
    return data["group"]


@group_bp.route("/group/name", methods=["PUT"])
@cross_origin(supports_credentials=True)
def update_group_name():
    session, err = require_session()
    if err:
        return err
    _, session_data = session

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return {"error": "invalid_name"}, 400

    mutation = """
        mutation UpdateGroupName($id: ID!, $name: String!) {
            updateGroup(where: {id: $id}, data: { name: $name }) { id }
        }
    """

    data = graphcms_request(
        session_data["bearer_token"],
        mutation,
        {"id": session_data["group_id"], "name": name},
    )
    if not data or not data.get("updateGroup"):
        return {"error": "api_unavailable"}, 502

    publish_group(session_data["bearer_token"], session_data["group_id"])
    return data["updateGroup"]


@group_bp.route("/group/participants", methods=["PUT"])
@cross_origin(supports_credentials=True)
def update_group_participants():
    session, err = require_session()
    if err:
        return err
    _, session_data = session

    payload = request.get_json(silent=True) or {}
    participants = payload.get("participants")
    if not isinstance(participants, list):
        return {"error": "invalid_payload"}, 400

    mutation = """
        mutation UpdateGroupParticipants($id: ID!, $participants: Json!) {
            updateGroup(where: {id: $id}, data: { participants: $participants }) { id }
        }
    """

    data = graphcms_request(
        session_data["bearer_token"],
        mutation,
        {"id": session_data["group_id"], "participants": participants},
    )
    if not data or not data.get("updateGroup"):
        return {"error": "api_unavailable"}, 502

    publish_group(session_data["bearer_token"], session_data["group_id"])
    return data["updateGroup"]


@group_bp.route("/group/events", methods=["PUT"])
@cross_origin(supports_credentials=True)
def update_group_events():
    session, err = require_session()
    if err:
        return err
    _, session_data = session

    payload = request.get_json(silent=True) or {}
    events = payload.get("events")
    if not isinstance(events, list):
        return {"error": "invalid_payload"}, 400

    mutation = """
        mutation UpdateGroupEvents($id: ID!, $events: Json!) {
            updateGroup(where: {id: $id}, data: { events: $events }) { id }
        }
    """

    data = graphcms_request(
        session_data["bearer_token"],
        mutation,
        {"id": session_data["group_id"], "events": events},
    )
    if not data or not data.get("updateGroup"):
        return {"error": "api_unavailable"}, 502

    publish_group(session_data["bearer_token"], session_data["group_id"])
    return data["updateGroup"]


@group_bp.route("/group/template", methods=["PUT"])
@cross_origin(supports_credentials=True)
def update_group_template():
    session, err = require_session()
    if err:
        return err
    _, session_data = session

    payload = request.get_json(silent=True) or {}
    template = payload.get("template")
    if not isinstance(template, dict):
        return {"error": "invalid_payload"}, 400

    mutation = """
        mutation UpdateGroupTemplate($id: ID!, $template: Json!) {
            updateGroup(where: {id: $id}, data: { template: $template }) { id }
        }
    """

    data = graphcms_request(
        session_data["bearer_token"],
        mutation,
        {"id": session_data["group_id"], "template": template},
    )
    if not data or not data.get("updateGroup"):
        return {"error": "api_unavailable"}, 502

    publish_group(session_data["bearer_token"], session_data["group_id"])
    return data["updateGroup"]
