import io
import os
import unittest
from unittest.mock import patch

os.environ.update(HYGRAPH_ADMIN_TOKEN='test', SESSION_SECRET_KEY='test', CORS_ORIGINS='https://allowed.example')
from app import create_app
from services.hygraph import HygraphUnavailable
from services.session_auth import start_session

SESSION = ((None, {'group_id':'group-a','bearer_token':'test'}), None)

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.app=create_app()
        self.app.testing=True
        self.client=self.app.test_client()
        self.network=patch('requests.post', side_effect=AssertionError('Network forbidden'))
        self.network.start()
        self.addCleanup(self.network.stop)

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

if __name__ == '__main__':
    unittest.main()
