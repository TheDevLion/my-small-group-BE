from datetime import date
from services.hygraph import graphcms_request, publish_group


def valid_id(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 128


def valid_participants(value):
    return (isinstance(value, list) and len(value) <= 30
        and all(isinstance(p, dict) and valid_id(p.get('id'))
            and isinstance(p.get('name'), str) and bool(p['name'].strip())
            and isinstance(p.get('alias'), str)
            and p.get('role') in ('leader', 'member', 'guest') for p in value)
        and len({p['id'] for p in value}) == len(value))


def valid_events(value):
    if not isinstance(value, list):
        return False
    ids = set()
    for event in value:
        if not isinstance(event, dict) or not valid_id(event.get('id')) or event['id'] in ids:
            return False
        ids.add(event['id'])
        if not isinstance(event.get('title'), str) or not event['title'].strip():
            return False
        if not isinstance(event.get('description'), str) or not isinstance(event.get('frequencyFlag'), bool):
            return False
        day = event.get('dateStr')
        try:
            if not isinstance(day, str) or len(day) != 10 or date.fromisoformat(day).isoformat() != day:
                return False
        except ValueError:
            return False
        presence = event.get('presence')
        if not isinstance(presence, list) or not all(valid_id(p) for p in presence) or len(set(presence)) != len(presence):
            return False
    return True


def valid_template(value):
    if not isinstance(value, dict):
        return False
    if 'shuffle_connector_word' in value:
        connector = value['shuffle_connector_word']
        if not isinstance(connector, str) or not connector.strip():
            return False
    if 'shuffle_dialog_font_size' in value:
        try:
            size = float(value['shuffle_dialog_font_size'])
            if isinstance(value['shuffle_dialog_font_size'], bool) or not 8 <= size <= 96:
                return False
        except (ValueError, TypeError):
            return False
    return True


def get_group_data(session):
    data = graphcms_request(session['bearer_token'], '''
        query GetGroup($id: ID!) {
            group(where: {id: $id}, stage: DRAFT) {
                id updatedAt name participants events template
            }
        }
    ''', {'id': session['group_id']})
    group = data.get('group') if isinstance(data, dict) else None
    if not isinstance(group, dict):
        return None
    for field, default in [('events', []), ('participants', []), ('template', {})]:
        if group.get(field) is None:
            group[field] = default
    if not isinstance(group['events'], list) or not isinstance(group['participants'], list):
        return None
    for event in group['events']:
        if not isinstance(event, dict) or not valid_id(event.get('id')):
            return None
        for field, default in [('title', ''), ('dateStr', ''), ('description', ''), ('presence', []), ('frequencyFlag', False)]:
            if event.get(field) is None:
                event[field] = default
        if (not all(isinstance(event[field], str) for field in ('title', 'dateStr', 'description'))
                or not isinstance(event['presence'], list) or not all(valid_id(p) for p in event['presence'])):
            return None
    for participant in group['participants']:
        if not isinstance(participant, dict) or not valid_id(participant.get('id')):
            return None
        for field in ('name', 'alias', 'role'):
            if participant.get(field) is None:
                participant[field] = ''
            if not isinstance(participant[field], str):
                return None
    if not isinstance(group['template'], dict):
        return None
    return group


def update_group_field(session, field, value, revision):
    current = get_group_data(session)
    if not current:
        return {'error': 'api_unavailable'}, 502
    if current.get('updatedAt') != revision:
        return {'error': 'conflict'}, 409
    if field in ('events', 'participants'):
        previous = {item['id']: item for item in current[field]}
        validator = valid_events if field == 'events' else valid_participants
        ids = set()
        for item in value:
            if not isinstance(item, dict) or not valid_id(item.get('id')) or item['id'] in ids:
                return {'error': 'invalid_payload'}, 400
            ids.add(item['id'])
            # Preserve untouched legacy records; enforce the current contract on edits.
            if item != previous.get(item['id']) and not validator([item]):
                return {'error': 'invalid_payload'}, 400
        if field == 'participants' and len(value) > max(30, len(current[field])):
            return {'error': 'invalid_payload'}, 400
    if field == 'participants':
        removed = {p['id'] for p in current.get('participants', [])} - {p['id'] for p in value}
        if any(removed.intersection(e.get('presence', [])) for e in current.get('events', [])):
            return {'error': 'participant_in_use'}, 409
    if field == 'events':
        participants = {p['id'] for p in current.get('participants', [])}
        historical = {e['id']: set(e.get('presence', [])) for e in current.get('events', [])}
        if any(set(e['presence']) - participants - historical.get(e['id'], set()) for e in value):
            return {'error': 'invalid_payload'}, 400
    # Match the revision inside the mutation, not only in the preceding read.
    value_type = 'String!' if field == 'name' else 'Json!'
    mutation = f'''
        mutation UpdateGroup($id: ID!, $revision: DateTime!, $value: {value_type}) {{
            updateManyGroupsConnection(
                where: {{id: $id, updatedAt: $revision}}, data: {{{field}: $value}}
            ) {{ edges {{ node {{ id updatedAt }} }} }}
        }}
    '''
    data = graphcms_request(session['bearer_token'], mutation,
        {'id': session['group_id'], 'revision': revision, 'value': value})
    if not data or not isinstance(data.get('updateManyGroupsConnection'), dict):
        return {'error': 'api_unavailable'}, 502
    edges = data['updateManyGroupsConnection'].get('edges')
    if edges is None:
        return {'error': 'api_unavailable'}, 502
    if not edges:
        return {'error': 'conflict'}, 409
    result = edges[0]['node']
    if not publish_group(session['bearer_token'], session['group_id']):
        return {'error': 'publication_failed'}, 502
    return result
