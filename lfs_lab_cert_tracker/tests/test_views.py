from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from urllib.parse import urlencode

from lfs_lab_cert_tracker import api

LOGIN_URL = reverse('local_login')
ContentType='application/x-www-form-urlencoded'

DATA = [
    'lfs_lab_cert_tracker/fixtures/users.json'
]

USERS = [ 'testadmin', 'testuser1']
PASSWORD = 'password'

class UserTest(TestCase):
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

    def test_edit_user(self):
        print('\n- Test: edit an user basic information')
        self.login()

        user = api.get_user_by_username(USERS[1])
        EMAIL = 'test.user1@example.com'

        # duplicated username
        data1 = {
            'username': USERS[0],
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': EMAIL,
            'user': user.id,
            'next': reverse('users') + '?t=all&page=2'
        }
        response = self.client.post(reverse('edit_user'), data=urlencode(data1, True), content_type=ContentType)
        messages = self.messages(response)
        self.assertTrue('Error' in messages[0])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('users') + '?t=all&page=2')
        self.assertRedirects(response, response.url)

        # invalid email
        data2 = {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'user': user.id,
            'next': reverse('users') + '?t=all&page=2'
        }
        response = self.client.post(reverse('edit_user'), data=urlencode(data2, True), content_type=ContentType)
        messages = self.messages(response)
        self.assertTrue('Error' in messages[0])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('users') + '?t=all&page=2')
        self.assertRedirects(response, response.url)

        # last name is empty
        data3 = {
            'username': user.username,
            'first_name': user.first_name,
            'email': EMAIL,
            'user': user.id,
            'next': reverse('users') + '?t=all&page=2'
        }
        response = self.client.post(reverse('edit_user'), data=urlencode(data3, True), content_type=ContentType)
        messages = self.messages(response)
        self.assertTrue('Error' in messages[0])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('users') + '?t=all&page=2')
        self.assertRedirects(response, response.url)

        # First name is long
        data4 = {
            'username': user.username,
            'first_name': 'abcdefgijlabcdefgijlabcdefgijlu',
            'last_name': user.last_name,
            'email': EMAIL,
            'user': user.id,
            'next': reverse('users') + '?t=all&page=2'
        }
        response = self.client.post(reverse('edit_user'), data=urlencode(data4, True), content_type=ContentType)
        messages = self.messages(response)
        self.assertTrue('Error' in messages[0])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('users') + '?t=all&page=2')
        self.assertRedirects(response, response.url)

        # ok
        data5 = {
            'username': 'edited' + user.username,
            'first_name': 'edited' + user.first_name,
            'last_name': 'edited' + user.last_name,
            'email': 'edited' + EMAIL,
            'user': user.id,
            'next': reverse('users') + '?t=all&page=2'
        }
        response = self.client.post(reverse('edit_user'), data=urlencode(data5, True), content_type=ContentType)
        messages = self.messages(response)
        self.assertTrue('Success' in messages[0])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('users') + '?t=all&page=2')
        self.assertRedirects(response, response.url)

        user = api.get_user_by_username(data5['username'])
        self.assertEqual(user.id, data5['user'])
        self.assertEqual(user.username, data5['username'])
        self.assertEqual(user.first_name, data5['first_name'])
        self.assertEqual(user.last_name, data5['last_name'])
        self.assertEqual(user.email, data5['email'])
