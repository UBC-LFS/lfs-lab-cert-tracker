from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from urllib.parse import urlencode
import json

from lfs_lab_cert_tracker.utils import Api

LOGIN_URL = reverse('local_login')
ContentType='application/x-www-form-urlencoded'

DATA = [
    'lfs_lab_cert_tracker/fixtures/certs.json',
    'lfs_lab_cert_tracker/fixtures/labs.json',
    'lfs_lab_cert_tracker/fixtures/users.json',
    'lfs_lab_cert_tracker/fixtures/user_certs.json',
    'lfs_lab_cert_tracker/fixtures/user_labs.json',
    'lfs_lab_cert_tracker/fixtures/lab_certs.json'
]

USERS = [ 'testadmin', 'testpi1', 'testuser1']
PASSWORD = 'password'


class UserCertTest(TestCase):
    fixtures = DATA

    @classmethod
    def setUpTestData(cls):
        cls.user = api.get_user_by_username(USERS[0])

    def login(self, username=None, password=None):
        if username and password:
            self.client.post(LOGIN_URL, data={'username': username, 'password': password})
        else:
            self.client.post(LOGIN_URL, data={'username': self.user.username, 'password': PASSWORD})

    def messages(self, res):
        return [m.message for m in get_messages(res.wsgi_request)]

    def test_delete_user_cert_admin(self):
        print('\n- Test: delete a cert of users for admins')

        # admin
        self.login()

        response = self.client.get(reverse('user_training_details', args=[11, 20]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['app_user'].id, 11)
        self.assertEqual(response.context['user_cert'].cert.id, 20)
        self.assertTrue(response.context['can_delete'])

        user_id = response.context['app_user'].id
        cert_id = response.context['user_cert'].cert.id
        data1 = { 'user': user_id, 'cert': cert_id }
        response = self.client.post(reverse('user_training_details', args=[user_id, cert_id]), data=urlencode(data1), content_type=ContentType)
        messages = self.messages(response)
        self.assertTrue('Success' in messages[0])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('user_certs', args=[user_id]))
        self.assertRedirects(response, response.url)

    def test_delete_user_cert_pi(self):
        print('\n- Test: delete a cert of users for pis')
        self.login(USERS[1], PASSWORD)

        response = self.client.get(reverse('user_training_details', args=[11, 20]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['app_user'].id, 11)
        self.assertEqual(response.context['user_cert'].cert.id, 20)
        self.assertFalse(response.context['can_delete'])

        user_id = response.context['app_user'].id
        cert_id = response.context['user_cert'].cert.id
        data1 = { 'user': user_id, 'cert': cert_id }
        response = self.client.post(reverse('user_training_details', args=[user_id, cert_id]), data=urlencode(data1), content_type=ContentType)
        messages = self.messages(response)
        self.assertTrue('Error' in messages[0])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('user_certs', args=[4]))
        self.assertRedirects(response, response.url)

    def test_delete_user_cert_user(self):
        print('\n- Test: delete a cert of users for users')
        self.login(USERS[2], PASSWORD)

        response = self.client.get(reverse('user_training_details', args=[11, 20]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['app_user'].id, 11)
        self.assertEqual(response.context['user_cert'].cert.id, 20)
        self.assertTrue(response.context['can_delete'])

        user_id = response.context['app_user'].id
        cert_id = response.context['user_cert'].cert.id
        data1 = { 'user': user_id, 'cert': cert_id }
        response = self.client.post(reverse('user_training_details', args=[user_id, cert_id]), data=urlencode(data1), content_type=ContentType)
        messages = self.messages(response)
        self.assertTrue('Success' in messages[0])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('user_certs', args=[user_id]))
        self.assertRedirects(response, response.url)
