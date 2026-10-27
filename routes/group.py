from flask import Blueprint, request
from services.group_data import get_group_data, update_group_field, valid_events, valid_participants, valid_template
from services.session_auth import require_session


group_bp = Blueprint('group', __name__)


@group_bp.route('/group', methods=['GET'])
def get_group():
    session, err = require_session()
    if err:
        return err
    data = get_group_data(session[1])
    if not data:
        return {'error': 'api_unavailable'}, 502
    return data


def _update(field, validate):
    session, err = require_session()
    if err:
        return err
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not validate(payload.get(field)):
        return {'error': 'invalid_payload'}, 400
    revision = payload.get('updatedAt')
    if not isinstance(revision, str) or not revision:
        return {'error': 'conflict'}, 409
    value = payload[field].strip() if field == 'name' else payload[field]
    return update_group_field(session[1], field, value, revision)


@group_bp.route('/group/name', methods=['PUT'])
def update_group_name():
    return _update('name', lambda value: isinstance(value, str) and bool(value.strip()))


@group_bp.route('/group/participants', methods=['PUT'])
def update_group_participants():
    return _update('participants', valid_participants)


@group_bp.route('/group/events', methods=['PUT'])
def update_group_events():
    return _update('events', valid_events)


@group_bp.route('/group/template', methods=['PUT'])
def update_group_template():
    return _update('template', valid_template)
