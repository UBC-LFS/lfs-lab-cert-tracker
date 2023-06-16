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
    
    # def test_api_call(self):
    #     print('\n- Test: check api call for one user')
    #     cwl = ""
        
    #     result = self.api.get_certificates_for_user(cwl)
    #     # Convert JSON string to Python object
    #     # data = json.loads(result)

    #     # Pretty print the JSON object #imeldac
    #     # pretty_json = json.dumps(data, indent=4)
    #     # print(pretty_json)
    #     results = json.dumps({'results': result})
    #     print(results)
    
    def test_api_threads(self):
        cwl_list = [] 

        # Maximum number of concurrent threads
        max_workers = 5
        cwl_errors = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.api.get_certificates_for_user, cwl) for cwl in cwl_list]

            for future, cwl in zip(futures, cwl_list):
                try:
                    result = future.result()  # Get the result of the completed future
                    print(result)
                except Exception as e:
                    print(f"An error occurred for CWL {cwl}: {str(e)}")
                    cwl_errors.append(cwl)

        # Print the list of CWLs with errors
        print("CWLs with errors:", cwl_errors)
        
    # def test_api_call_multiple_cwls(self):
    #     print('\n- Test: check api call for multiple users')
    #     cwls = []
        
    #     result = self.api.get_certificates_for_cwls_at_once(cwls)
    #     print("RESULT IS", result)
    #     print("LENGTH IS", len(result))

        
        
        