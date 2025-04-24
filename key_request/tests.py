from django.test import TestCase, tag
from django.urls import reverse
from django.contrib.messages import get_messages
import json



LOGIN_URL = reverse('accounts:local_login')

USERS = ['testadmin', 'testpi1', 'testuser1']
PASSWORD = 'password'

DATA = [
    'app/fixtures/certs.json',
    'app/fixtures/labs.json',
    'app/fixtures/users.json',
    'app/fixtures/user_certs.json',
    'app/fixtures/user_labs.json',
    'app/fixtures/lab_certs.json',
    'key_request/fixtures/buildings.json',
    'key_request/fixtures/floors.json',
    'key_request/fixtures/rooms.json',
]

class KeyRequestTest(TestCase):
    fixtures = DATA

    def login(self, username):
        self.client.post(LOGIN_URL, data={'username': username, 'password': PASSWORD})
    
    def messages(self, res):
        return [m.message for m in get_messages(res.wsgi_request)]
    
    def json_messages(self, res):
        return json.loads(res.content.decode('utf-8'))


    @tag('one')
    def test_one(self):
        print('\n- Test: one')
        self.login(USERS[2])

        res = self.client.get(reverse('key_request:index'))
        print(res)

