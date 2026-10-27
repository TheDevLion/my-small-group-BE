import io
import os
import unittest
from unittest.mock import patch

os.environ.update(HYGRAPH_ADMIN_TOKEN='test', SESSION_SECRET_KEY='test', CORS_ORIGINS='https://allowed.example')
from app import create_app
from services.hygraph import HygraphUnavailable
from services.session_auth import start_session

SESSION = ((None, {'group_id':'group-a','bearer_token':'test'}), None)

class BaseTests(unittest.TestCase):
    def setUp(self):
        self.app=create_app()
        self.app.testing=True
        self.client=self.app.test_client()
        self.network=patch('requests.post', side_effect=AssertionError('Network forbidden'))
        self.network.start()
        self.addCleanup(self.network.stop)

class ApiTests(BaseTests):
    def test_cors_allows_only_configured_origins(self):
        for origin, allowed in [('https://allowed.example',True),('https://untrusted.example',False)]:
            r=self.client.options('/group/events', headers={'Origin':origin,'Access-Control-Request-Method':'PUT'})
            self.assertEqual(r.headers.get('Access-Control-Allow-Origin'),origin if allowed else None)

    def test_token_outage_preserves_session(self):
        self.client.set_cookie('msg_session',start_session('group-a'))
        with patch('services.session_auth.get_bearer_token_by_group',side_effect=HygraphUnavailable()):
            self.assertEqual(self.client.get('/group').status_code,503)
        with patch('routes.auth.get_bearer_token',side_effect=HygraphUnavailable()):
            self.assertEqual(self.client.post('/login',json={'payload':'pw'}).status_code,503)
        with patch('routes.auth.get_bearer_token',return_value=None):
            self.assertEqual(self.client.post('/login',json={'payload':'pw'}).status_code,401)

    def test_cookie_from_another_group_cannot_write(self):
        self.client.set_cookie('msg_session',start_session('group-b'))
        with patch('services.session_auth.get_bearer_token_by_group') as token:
            self.assertEqual(self.client.put('/group/events',json={'events':[]},headers={'X-Group-ID':'group-a'}).status_code,401)
            token.assert_not_called()

    def test_login_rejects_non_object_body(self):
        self.assertEqual(self.client.post('/login',json=['bad']).status_code,400)

class GroupTests(BaseTests):
    def setUp(self):
        super().setUp()
        self.auth=patch('routes.group.require_session',return_value=SESSION)
        self.auth.start(); self.addCleanup(self.auth.stop)
        self.current={'id':'group-a','updatedAt':'2026-10-27T10:00:00Z','events':[], 'participants':[]}

    def test_nullable_empty_group_loads_without_breaking_writes(self):
        from services.group_data import get_group_data
        with patch('services.group_data.graphcms_request', return_value={'group': {'id':'group-a','events':None,'participants':None,'template':None}}):
            group=get_group_data(SESSION[0][1])
            self.assertEqual(group['events'],[])
            self.assertEqual(group['participants'],[])
            self.assertEqual(group['template'],{})

    def test_success_returns_the_written_revision(self):
        result={'id':'group-a','updatedAt':'2026-10-27T10:00:01Z'}
        with patch('services.group_data.get_group_data',return_value=self.current), patch('services.group_data.graphcms_request',return_value={'updateManyGroupsConnection':{'edges':[{'node':result}]}}), patch('services.group_data.publish_group',return_value={'id':'group-a'}):
            r=self.client.put('/group/events',json={'events':[],'updatedAt':self.current['updatedAt']})
            self.assertEqual(r.status_code,200)
            self.assertEqual(r.json,result)

    def test_invalid_records_never_reach_storage(self):
        for field,value in [('events',[None]),('events',[{'id':'e'}]),('participants',[{'id':'p','role':''}]),('template',{'shuffle_dialog_font_size':'huge'}),('name',123)]:
            with patch('services.group_data.graphcms_request') as call:
                self.assertEqual(self.client.put('/group/'+field,json={field:value}).status_code,400)
                call.assert_not_called()

    def test_revision_is_required_and_stale_writes_conflict(self):
        self.assertEqual(self.client.put('/group/events',json={'events':[]}).status_code,409)
        with patch('services.group_data.get_group_data',return_value=self.current), patch('services.group_data.graphcms_request') as call:
            self.assertEqual(self.client.put('/group/events',json={'events':[],'updatedAt':'old'}).status_code,409)
            call.assert_not_called()

    def test_racing_writes_are_conditional_in_storage(self):
        with patch('services.group_data.get_group_data',return_value=self.current), patch('services.group_data.graphcms_request',return_value={'updateManyGroupsConnection':{'edges':[]}}) as call:
            r=self.client.put('/group/events',json={'events':[],'updatedAt':self.current['updatedAt']})
            self.assertEqual(r.status_code,409)
            self.assertIn('updatedAt: $revision',call.call_args.args[1])
            self.assertEqual(call.call_args.args[2]['revision'],self.current['updatedAt'])

    def test_publication_failure_is_not_success(self):
        data={'updateManyGroupsConnection':{'edges':[{'node':{'id':'group-a','updatedAt':'new'}}]}}
        with patch('services.group_data.get_group_data',return_value=self.current), patch('services.group_data.graphcms_request',return_value=data), patch('services.group_data.publish_group',return_value=None):
            r=self.client.put('/group/events',json={'events':[],'updatedAt':self.current['updatedAt']})
            self.assertEqual(r.status_code,502)
            self.assertEqual(r.json['error'],'publication_failed')

    def test_participant_with_attendance_cannot_be_deleted(self):
        self.current.update(participants=[{'id':'p'}],events=[{'id':'e','presence':['p']}])
        with patch('services.group_data.get_group_data',return_value=self.current), patch('services.group_data.graphcms_request') as call:
            r=self.client.put('/group/participants',json={'participants':[],'updatedAt':self.current['updatedAt']})
            self.assertEqual(r.status_code,409)
            self.assertEqual(r.json['error'],'participant_in_use')
            call.assert_not_called()

class PhotoTests(BaseTests):
    def setUp(self):
        super().setUp()
        self.auth=patch('routes.event_photos.require_session',return_value=SESSION)
        self.auth.start(); self.addCleanup(self.auth.stop)

    def test_foreign_event_is_rejected_before_upload(self):
        with patch('routes.event_photos.get_group_data',return_value={'events':[]}), patch('routes.event_photos.upload_asset') as upload:
            r=self.client.post('/event-photos',data={'eventId':'foreign','fileUpload':(io.BytesIO(b'GIF89a' + b'0'*30),'a.gif')})
            self.assertEqual(r.status_code,404)
            upload.assert_not_called()

    def test_invalid_file_is_rejected(self):
        with patch('routes.event_photos.upload_asset') as upload:
            r=self.client.post('/event-photos',data={'eventId':'e','fileUpload':(io.BytesIO(b'not image'),'a.png')})
            self.assertEqual(r.status_code,400)
            upload.assert_not_called()

    def test_foreign_photo_cannot_be_deleted_or_published(self):
        with patch('routes.event_photos.graphcms_request',return_value={'eventPhotos':[]}) as query:
            self.assertEqual(self.client.delete('/event-photos/foreign').status_code,404)
            self.assertEqual(self.client.post('/event-photos/foreign/publish').status_code,404)
            self.assertEqual(query.call_count,2)
            self.assertIn('groupId: $groupId',query.call_args.args[1])
            self.assertEqual(query.call_args.args[2]['groupId'],'group-a')

    def test_partial_upload_returns_retryable_id(self):
        photo={'id':'photo','img':{'id':'asset','url':'url'}}
        with patch('routes.event_photos.get_group_data',return_value={'events':[{'id':'e'}]}), patch('routes.event_photos.upload_asset',return_value={'id':'asset'}), patch('routes.event_photos.graphcms_request',return_value={'createEventPhoto':photo}), patch('routes.event_photos.publish_asset',return_value=None):
            r=self.client.post('/event-photos',data={'eventId':'e','fileUpload':(io.BytesIO(b'GIF89a' + b'0'*30),'a.gif')})
            self.assertEqual(r.status_code,502)
            self.assertEqual(r.json,{'error':'publication_failed','id':'photo'})

    def test_publication_retry_reuses_existing_photo(self):
        photo={'id':'photo','eventId':'e','img':{'id':'asset','url':'url'}}
        with patch('routes.event_photos.get_group_data',return_value={'events':[{'id':'e'}]}), patch('routes.event_photos.graphcms_request',return_value={'eventPhotos':[photo]}) as query, patch('routes.event_photos.publish_asset',return_value={'id':'asset'}), patch('routes.event_photos.publish_event_photo',return_value={'id':'photo'}), patch('routes.event_photos.upload_asset') as upload:
            r=self.client.post('/event-photos/photo/publish')
            self.assertEqual(r.status_code,200)
            self.assertEqual(r.json,{'id':'photo','url':'url'})
            upload.assert_not_called()
            self.assertEqual(query.call_count,1)

    def test_listing_is_scoped_and_marks_pending_publication(self):
        with patch('routes.event_photos.get_group_data',return_value={'events':[{'id':'e'}]}), patch('routes.event_photos.graphcms_request',return_value={'eventPhotos':[{'id':'photo','img':{'url':'url'},'documentInStages':[]}]}) as query:
            r=self.client.get('/event-photos?eventId=e')
            self.assertEqual(r.status_code,200)
            self.assertTrue(r.json[0]['pending'])
            self.assertEqual(query.call_args.args[2]['groupId'],'group-a')

    def test_non_json_upload_response_is_handled(self):
        from services.hygraph import upload_asset
        from werkzeug.datastructures import FileStorage
        with patch('services.hygraph.requests.post') as request:
            request.return_value.ok=True
            request.return_value.json.side_effect=ValueError()
            self.assertIsNone(upload_asset('test',FileStorage(io.BytesIO(b'abc'),filename='a.png')))

if __name__ == '__main__':
    unittest.main()
