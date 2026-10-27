from flask import Blueprint, request
from services.hygraph import graphcms_request, publish_asset, publish_event_photo, upload_asset
from services.group_data import get_group_data
from services.session_auth import require_session


event_photos_bp = Blueprint('event_photos', __name__)
MAX_PHOTO_BYTES = 4 * 1024 * 1024


def _event_error(session, event_id):
    group = get_group_data(session)
    if not group:
        return {'error': 'api_unavailable'}, 502
    if not any(e.get('id') == event_id for e in group.get('events', []) if isinstance(e, dict)):
        return {'error': 'not_found'}, 404
    return None


def _photo(session, photo_id):
    data = graphcms_request(session['bearer_token'], '''
        query Photo($id: ID!, $groupId: String!) {
            eventPhotos(where: {id: $id, groupId: $groupId}, stage: DRAFT, first: 1) {
                id eventId img { id url }
            }
        }
    ''', {'id': photo_id, 'groupId': session['group_id']})
    if data is None:
        return None, ({'error': 'api_unavailable'}, 502)
    photos = data.get('eventPhotos', [])
    if not photos:
        return None, ({'error': 'not_found'}, 404)
    return photos[0], None


def _publish(session, photo):
    asset = photo.get('img') or {}
    if not asset.get('id') or not asset.get('url'):
        return {'error': 'api_unavailable'}, 502
    if not publish_asset(session['bearer_token'], asset['id']) or not publish_event_photo(session['bearer_token'], photo['id']):
        return {'error': 'publication_failed', 'id': photo['id']}, 502
    return {'id': photo['id'], 'url': asset['url']}


def _valid_image(file):
    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)
    header = file.stream.read(16)
    file.stream.seek(0)
    if not 0 < size <= MAX_PHOTO_BYTES:
        return False
    return (header.startswith(b'\xff\xd8\xff') or header.startswith(b'\x89PNG\r\n\x1a\n')
        or header.startswith((b'GIF87a', b'GIF89a'))
        or (header[:4] == b'RIFF' and header[8:12] == b'WEBP'))


@event_photos_bp.route('/event-photos', methods=['GET'])
def get_event_photos():
    session, err = require_session()
    if err:
        return err
    session = session[1]
    event_id = request.args.get('eventId')
    if not event_id:
        return {'error': 'missing_event_id'}, 400
    err = _event_error(session, event_id)
    if err:
        return err
    photos = []
    cursor = None
    while True:
        data = graphcms_request(session['bearer_token'], '''
            query Photos($eventId: String!, $groupId: String!, $after: ID) {
                eventPhotos(where: {eventId: $eventId, groupId: $groupId}, stage: PUBLISHED,
                    first: 100, after: $after, orderBy: id_ASC) {
                    id img { url }
                }
            }
        ''', {'eventId': event_id, 'groupId': session['group_id'], 'after': cursor})
        if not data or 'eventPhotos' not in data:
            return {'error': 'api_unavailable'}, 502
        batch = data['eventPhotos']
        photos.extend({'id': p['id'], 'url': (p.get('img') or {}).get('url')} for p in batch)
        if len(batch) < 100:
            return photos
        cursor = batch[-1]['id']


@event_photos_bp.route('/event-photos', methods=['POST'])
def upload_event_photo():
    session, err = require_session()
    if err:
        return err
    session = session[1]
    event_id = request.form.get('eventId')
    file = request.files.get('fileUpload') or request.files.get('file')
    if not event_id or not file:
        return {'error': 'missing_payload'}, 400
    if not _valid_image(file):
        return {'error': 'invalid_image'}, 400
    err = _event_error(session, event_id)
    if err:
        return err
    asset = upload_asset(session['bearer_token'], file)
    if not asset or not asset.get('id'):
        return {'error': 'api_unavailable'}, 502
    data = graphcms_request(session['bearer_token'], '''
        mutation CreatePhoto($groupId: String!, $eventId: String!, $assetId: ID!) {
            createEventPhoto(data: {groupId: $groupId, eventId: $eventId,
                img: {connect: {id: $assetId}}}) { id img { id url } }
        }
    ''', {'groupId': session['group_id'], 'eventId': event_id, 'assetId': asset['id']})
    if not data or not data.get('createEventPhoto'):
        return {'error': 'api_unavailable'}, 502
    return _publish(session, data['createEventPhoto'])


@event_photos_bp.route('/event-photos/<photo_id>/publish', methods=['POST'])
def retry_publication(photo_id):
    session, err = require_session()
    if err:
        return err
    session = session[1]
    photo, err = _photo(session, photo_id)
    if err:
        return err
    err = _event_error(session, photo.get('eventId'))
    if err:
        return err
    return _publish(session, photo)


@event_photos_bp.route('/event-photos/<photo_id>', methods=['DELETE'])
def delete_event_photo(photo_id):
    session, err = require_session()
    if err:
        return err
    session = session[1]
    photo, err = _photo(session, photo_id)
    if err:
        return err
    # Keep the existing deletion semantics: only published photos are listed.
    data = graphcms_request(session['bearer_token'], '''
        mutation UnpublishPhoto($id: ID!) {
            unpublishEventPhoto(where: {id: $id}) { id }
        }
    ''', {'id': photo_id})
    if not data or not data.get('unpublishEventPhoto'):
        return {'error': 'api_unavailable'}, 502
    return data['unpublishEventPhoto']
