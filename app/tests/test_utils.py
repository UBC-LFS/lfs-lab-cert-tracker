from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from urllib.parse import urlencode

import json

from app.utils import Api
from app.tests.test_users import LOGIN_URL, ContentType, DATA, USERS, PASSWORD


class AreaTest(TestCase):
    fixtures = DATA
    
    def setUp(self):
        self.api = Api()
    
    def test_api_call(self):
        print('\n- Test: check api call for one user')
        cwl = "wtamagi"
        
        result = self.api.get_certificates_for_user(cwl)
        self.assertEqual(result.status_code, 200)
        print("RESULT IS", result.json())
        
    # def test_api_call_multiple_cwls(self):
    #     print('\n- Test: check api call for multiple users')
    #     cwls = ["wtamagi", "wkang01", "hs55555"]
        
    #     result = self.api.get_certificates_for_cwls(cwls)
    #     print("RESULT IS", result)
        
        
        