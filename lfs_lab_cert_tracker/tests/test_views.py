from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from urllib.parse import urlencode

from lfs_lab_cert_tracker import api

LOGIN_URL = reverse('local_login')
ContentType='application/x-www-form-urlencoded'

DATA = [
    'lfs_lab_cert_tracker/fixtures/certs.json',
    'lfs_lab_cert_tracker/fixtures/labs.json',
    'lfs_lab_cert_tracker/fixtures/users.json',
    'lfs_lab_cert_tracker/fixtures/user_certs.json',
    'lfs_lab_cert_tracker/fixtures/user_labs.json'
]

USERS = [ 'testadmin', 'testpi1', 'testuser1']
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

        user = api.get_user_by_username(USERS[2])
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
        response = self.client.post(reverse('edit_user'), data=urlencode(data1), content_type=ContentType)
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
        response = self.client.post(reverse('edit_user'), data=urlencode(data2), content_type=ContentType)
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
        response = self.client.post(reverse('edit_user'), data=urlencode(data4), content_type=ContentType)
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
        response = self.client.post(reverse('edit_user'), data=urlencode(data5), content_type=ContentType)
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

        response = self.client.get(reverse('user_cert_details', args=[11, 20]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['app_user'].id, 11)
        self.assertEqual(response.context['user_cert'].cert.id, 20)
        self.assertTrue(response.context['can_delete'])

        user_id = response.context['app_user'].id
        cert_id = response.context['user_cert'].cert.id
        data1 = { 'user': user_id, 'cert': cert_id }
        response = self.client.post(reverse('user_cert_details', args=[user_id, cert_id]), data=urlencode(data1), content_type=ContentType)
        messages = self.messages(response)
        self.assertTrue('Success' in messages[0])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('user_certs', args=[user_id]))
        self.assertRedirects(response, response.url)

    def test_delete_user_cert_pi(self):
        print('\n- Test: delete a cert of users for pis')
        self.login(USERS[1], PASSWORD)

        response = self.client.get(reverse('user_cert_details', args=[11, 20]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['app_user'].id, 11)
        self.assertEqual(response.context['user_cert'].cert.id, 20)
        self.assertFalse(response.context['can_delete'])

        user_id = response.context['app_user'].id
        cert_id = response.context['user_cert'].cert.id
        data1 = { 'user': user_id, 'cert': cert_id }
        response = self.client.post(reverse('user_cert_details', args=[user_id, cert_id]), data=urlencode(data1), content_type=ContentType)
        messages = self.messages(response)
        self.assertTrue('Error' in messages[0])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('user_certs', args=[4]))
        self.assertRedirects(response, response.url)

    def test_delete_user_cert_user(self):
        print('\n- Test: delete a cert of users for users')
        self.login(USERS[2], PASSWORD)

        response = self.client.get(reverse('user_cert_details', args=[11, 20]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['app_user'].id, 11)
        self.assertEqual(response.context['user_cert'].cert.id, 20)
        self.assertTrue(response.context['can_delete'])

        user_id = response.context['app_user'].id
        cert_id = response.context['user_cert'].cert.id
        data1 = { 'user': user_id, 'cert': cert_id }
        response = self.client.post(reverse('user_cert_details', args=[user_id, cert_id]), data=urlencode(data1), content_type=ContentType)
        messages = self.messages(response)
        self.assertTrue('Success' in messages[0])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('user_certs', args=[user_id]))
        self.assertRedirects(response, response.url)
