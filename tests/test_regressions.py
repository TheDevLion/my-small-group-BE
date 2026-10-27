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

    def test_login_rejects_non_object_body(self):
        self.assertEqual(self.client.post('/login',json=['bad']).status_code,400)

class GroupTests(BaseTests):
    def setUp(self):
        super().setUp()
        self.auth=patch('routes.group.require_session',return_value=SESSION)
        self.auth.start(); self.addCleanup(self.auth.stop)
        self.current={'id':'group-a','updatedAt':'2026-10-27T10:00:00Z','events':[], 'participants':[]}

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

if __name__ == '__main__':
    unittest.main()
