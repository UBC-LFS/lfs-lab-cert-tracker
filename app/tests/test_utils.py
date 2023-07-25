from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from urllib.parse import urlencode

import json

from app.utils import Api
from app.tests.test_users import LOGIN_URL, ContentType, DATA, USERS, PASSWORD

import concurrent.futures

class AreaTest(TestCase):
    fixtures = DATA
    
    def setUp(self):
        self.api = Api()
        
    def test_api_call_multiple_cwls(self):
        print('\n- Test: check api call for multiple users')
        cwls = []
        
        result = self.api.get_certificates_for_cwls(cwls)
        print("LENGTH IS", len(result))
        for item in result:
            cwl = item['requestedIdentifier']['identifier']
            print("CWL IS", cwl)
            

        
        
        