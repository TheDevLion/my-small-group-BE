from flask import Blueprint, request
from flask_cors import cross_origin

from services.hygraph import (
    graphcms_request,
    publish_asset,
    publish_event_photo,
    upload_asset,
)
from services.session_auth import require_session


event_photos_bp = Blueprint("event_photos", __name__)


@event_photos_bp.route("/event-photos", methods=["GET"])
@cross_origin(supports_credentials=True)
def get_event_photos():
    session, err = require_session()
    if err:
        return err
    _, session_data = session

    event_id = request.args.get("eventId")
    if not event_id:
        return {"error": "missing_event_id"}, 400

    query = """
        query EventPhotos($eventId: String!) {
            eventPhotos(where: {eventId: $eventId}) {
                id
                img { url }
            }
        }
    """

    data = graphcms_request(
        session_data["bearer_token"],
        query,
        {"eventId": event_id},
    )
    if not data:
        return {"error": "api_unavailable"}, 502

    event_photos = data.get("eventPhotos", [])
    return [
        {"id": item.get("id"), "url": (item.get("img") or {}).get("url")}
        for item in event_photos
    ]


@event_photos_bp.route("/event-photos", methods=["POST"])
@cross_origin(supports_credentials=True)
def upload_event_photo():
    session, err = require_session()
    if err:
        return err
    _, session_data = session

    event_id = request.form.get("eventId") or request.args.get("eventId")
    file = request.files.get("fileUpload") or request.files.get("file")
    if not event_id or not file:
        return {"error": "missing_payload"}, 400

    upload_data = upload_asset(session_data["bearer_token"], file)
    if not upload_data:
        return {"error": "api_unavailable"}, 502

    asset_id = upload_data.get("id")
    if not asset_id:
        return {"error": "api_unavailable"}, 502

    mutation = """
        mutation CreateEventPhoto($groupId: String!, $eventId: String!, $assetId: ID!) {
            createEventPhoto(data: {
                groupId: $groupId,
                eventId: $eventId,
                img: { connect: { id: $assetId } }
            }) {
                id
                img { url }
            }
        }
    """

    data = graphcms_request(
        session_data["bearer_token"],
        mutation,
        {
            "groupId": session_data["group_id"],
            "eventId": event_id,
            "assetId": asset_id,
        },
    )
    if not data or not data.get("createEventPhoto"):
        return {"error": "api_unavailable"}, 502

    publish_asset(session_data["bearer_token"], asset_id)
    publish_event_photo(session_data["bearer_token"], data["createEventPhoto"]["id"])

    return {
        "id": data["createEventPhoto"]["id"],
        "url": data["createEventPhoto"]["img"]["url"],
    }


@event_photos_bp.route("/event-photos/<event_photo_id>", methods=["DELETE"])
@cross_origin(supports_credentials=True)
def delete_event_photo(event_photo_id):
    session, err = require_session()
    if err:
        return err
    _, session_data = session

    mutation = """
        mutation UnpublishEventPhoto($id: ID!) {
            unpublishEventPhoto(where: {id: $id}) { id }
        }
    """

    data = graphcms_request(
        session_data["bearer_token"],
        mutation,
        {"id": event_photo_id},
    )
    if not data or not data.get("unpublishEventPhoto"):
        return {"error": "api_unavailable"}, 502

    return data["unpublishEventPhoto"]
