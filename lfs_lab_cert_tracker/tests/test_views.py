from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from urllib.parse import urlencode
import json

from lfs_lab_cert_tracker import api

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
            'next': reverse('all_users') + '?page=2'
        }
        response = self.client.post(reverse('edit_user'), data=urlencode(data1), content_type=ContentType)
        messages = self.messages(response)
        self.assertTrue('Error' in messages[0])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('all_users') + '?page=2')
        self.assertRedirects(response, response.url)

        # invalid email
        data2 = {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'user': user.id,
            'next': reverse('all_users') + '?page=2'
        }
        response = self.client.post(reverse('edit_user'), data=urlencode(data2), content_type=ContentType)
        messages = self.messages(response)
        self.assertTrue('Error' in messages[0])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('all_users') + '?page=2')
        self.assertRedirects(response, response.url)

        # First name is long
        data4 = {
            'username': user.username,
            'first_name': 'abcdefgijlabcdefgijlabcdefgijlu',
            'last_name': user.last_name,
            'email': EMAIL,
            'user': user.id,
            'next': reverse('all_users') + '?page=2'
        }
        response = self.client.post(reverse('edit_user'), data=urlencode(data4), content_type=ContentType)
        messages = self.messages(response)
        self.assertTrue('Error' in messages[0])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('all_users') + '?page=2')
        self.assertRedirects(response, response.url)

        # ok
        data5 = {
            'username': 'edited' + user.username,
            'first_name': 'edited' + user.first_name,
            'last_name': 'edited' + user.last_name,
            'email': 'edited' + EMAIL,
            'user': user.id,
            'next': reverse('all_users') + '?page=2'
        }
        response = self.client.post(reverse('edit_user'), data=urlencode(data5), content_type=ContentType)
        messages = self.messages(response)
        self.assertTrue('Success' in messages[0])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('all_users') + '?page=2')
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


class UserLabTest(TestCase):
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

    def json_messages(self, res):
        return json.loads( res.content.decode('utf-8') )


    def test_assign_areas_to_user_one_selected(self):
        print('\n- Test: Assign areas to an user - one selected')
        self.login()

        self.assertEqual(self.user.userlab_set.count(), 0)

        data1 = {
            'user': self.user.id,
            'areas[]': ['2,1']
        }
        res = self.client.post( reverse('assign_user_areas'), data=urlencode(data1, True), content_type=ContentType )
        self.assertEqual(res.status_code, 200)
        messages = self.json_messages(res)
        self.assertEqual(messages['status'], 'success')
        self.assertEqual(messages['message'], "Success! test admin's Areas have changed. Please see the following status: <ul class='mb-0'><li>Added: Bio Lab</li></ul>")

        userlabs1 = self.user.userlab_set.all()
        self.assertEqual(len(userlabs1), 1)
        self.assertEqual(userlabs1.first().lab.name, 'Bio Lab')
        self.assertEqual(userlabs1.first().role, 1)


        # test.user1
        user = api.get_user_404(11)
        self.assertEqual(user.userlab_set.count(), 2)

        data2 = {
            'user': user.id,
            'areas[]': ['3,1']
        }
        res = self.client.post( reverse('assign_user_areas'), data=urlencode(data2, True), content_type=ContentType )
        self.assertEqual(res.status_code, 200)
        messages = self.json_messages(res)
        self.assertEqual(messages['status'], 'success')
        self.assertEqual(messages['message'], "Success! test user1's Areas have changed. Please see the following status: <ul class='mb-0'><li>Added: Chemistry Lab</li><li>Deleted: Learning Centre, Bio Lab</li></ul>")

        userlabs2 = user.userlab_set.all()
        self.assertEqual(userlabs2.first().lab.name, 'Chemistry Lab')
        self.assertEqual(userlabs2.first().role, 1)


    def test_assign_areas_to_user_two_selected(self):
        print('\n- Test: Assign areas to an user - two selected')
        self.login()

        userlabs = self.user.userlab_set.count()
        self.assertEqual(self.user.userlab_set.count(), 0)

        data = {
            'user': self.user.id,
            'areas[]': ['2,0', '3,0']
        }
        res = self.client.post( reverse('assign_user_areas'), data=urlencode(data, True), content_type=ContentType )
        self.assertEqual(res.status_code, 200)
        messages = self.json_messages(res)
        self.assertEqual(messages['status'], 'success')
        self.assertEqual(messages['message'], "Success! test admin's Areas have changed. Please see the following status: <ul class='mb-0'><li>Added: Bio Lab, Chemistry Lab</li></ul>")

        userlabs = self.user.userlab_set.all()
        self.assertEqual(len(userlabs), 2)

        labs = []
        roles = []
        for userlab in userlabs:
            labs.append(userlab.lab.name)
            roles.append(userlab.role)

        self.assertEqual(labs[0], 'Bio Lab')
        self.assertEqual(roles[0], 0)
        self.assertEqual(labs[1], 'Chemistry Lab')
        self.assertEqual(roles[1], 0)


    def test_assign_areas_to_user_nothing_selected(self):
        print('\n- Test: Assign areas to an user - nothing selected')
        self.login()

        userlabs = self.user.userlab_set.count()
        self.assertEqual(self.user.userlab_set.count(), 0)

        data = {
            'user': self.user.id,
            'areas[]': []
        }
        res = self.client.post( reverse('assign_user_areas'), data=urlencode(data, True), content_type=ContentType )
        self.assertEqual(res.status_code, 200)
        messages = self.json_messages(res)
        self.assertEqual(messages['status'], 'warning')
        self.assertEqual(messages['message'], "Warning! Nothing has changed.")

        userlabs = self.user.userlab_set.count()
        self.assertEqual(self.user.userlab_set.count(), 0)


    def test_assign_areas_to_user_nothing_selected(self):
        print('\n- Test: Assign areas to an user - existing area unchecked')
        self.login()

        user = api.get_user_404(11)
        userlabs = user.userlab_set.count()
        self.assertEqual(user.userlab_set.count(), 2)

        data = {
            'user': self.user.id,
            'areas[]': []
        }
        res = self.client.post( reverse('assign_user_areas'), data=urlencode(data, True), content_type=ContentType )
        self.assertEqual(res.status_code, 200)
        messages = self.json_messages(res)
        self.assertEqual(messages['status'], 'warning')
        self.assertEqual(messages['message'], "Warning! Nothing has changed.")

        userlabs = self.user.userlab_set.count()
        self.assertEqual(self.user.userlab_set.count(), 0)



    def test_assign_areas_to_user_all_selected(self):
        print('\n- Test: Assign areas to an user - all selected')
        self.login()

        user = api.get_user_404(11)
        userlabs = user.userlab_set.count()
        self.assertEqual(user.userlab_set.count(), 2)

        data = {
            'user': user.id,
            'areas[]': ['1,0','2,0','3,0','4,1','5,1']
        }
        res = self.client.post( reverse('assign_user_areas'), data=urlencode(data, True), content_type=ContentType )
        messages = self.json_messages(res)
        self.assertEqual(messages['status'], 'success')
        self.assertEqual(messages['message'], "Success! test user1's Areas have changed. Please see the following status: <ul class='mb-0'><li>Added: Chemistry Lab, Food Lab, Safety Lab</li></ul>")

        userlabs = user.userlab_set.all()
        self.assertEqual(len(userlabs), 5)

        labs = []
        roles = []
        for userlab in userlabs:
            labs.append(userlab.lab.name)
            roles.append(userlab.role)

        self.assertEqual(labs, ['Learning Centre', 'Bio Lab', 'Chemistry Lab', 'Food Lab', 'Safety Lab'])
        self.assertEqual(roles, [0, 0, 0, 1, 1])

    def test_assign_areas_to_user_all_selected_change_role(self):
        print('\n- Test: Assign areas to an user - all selected and change role')
        self.login()

        self.assertEqual(self.user.userlab_set.count(), 0)

        data1 = {
            'user': self.user.id,
            'areas[]': ['1,0','2,0','3,0','4,1','5,1']
        }
        res = self.client.post( reverse('assign_user_areas'), data=urlencode(data1, True), content_type=ContentType )
        self.assertEqual(res.status_code, 200)
        messages = self.json_messages(res)
        self.assertEqual(messages['status'], 'success')
        self.assertEqual(messages['message'], "Success! test admin's Areas have changed. Please see the following status: <ul class='mb-0'><li>Added: Learning Centre, Bio Lab, Chemistry Lab, Food Lab, Safety Lab</li></ul>")

        userlabs1 = self.user.userlab_set.all()
        self.assertEqual(len(userlabs1), 5)

        labs1 = []
        roles1 = []
        for userlab in userlabs1:
            labs1.append(userlab.lab.name)
            roles1.append(userlab.role)

        self.assertEqual(labs1, ['Learning Centre', 'Bio Lab', 'Chemistry Lab', 'Food Lab', 'Safety Lab'])
        self.assertEqual(roles1, [0, 0, 0, 1, 1])

        data2 = {
            'user': self.user.id,
            'areas[]': ['1,1','2,1','3,0','4,0','5,1']
        }
        res = self.client.post( reverse('assign_user_areas'), data=urlencode(data2, True), content_type=ContentType )
        self.assertEqual(res.status_code, 200)
        messages = self.json_messages(res)
        self.assertEqual(messages['status'], 'success')
        self.assertEqual(messages['message'], "Success! test admin's Areas have changed. Please see the following status: <ul class='mb-0'><li>Changed: Learning Centre, Bio Lab, Food Lab</li></ul>")

        userlabs2 = self.user.userlab_set.all()
        self.assertEqual(len(userlabs2), 5)

        labs2 = []
        roles2 = []
        for userlab in userlabs2:
            labs2.append(userlab.lab.name)
            roles2.append(userlab.role)

        self.assertEqual(labs2, ['Learning Centre', 'Bio Lab', 'Chemistry Lab', 'Food Lab', 'Safety Lab'])
        self.assertEqual(roles2, [1, 1, 0, 0, 1])


    def test_assign_areas_to_user_all_selected_unchecked(self):
        print('\n- Test: Assign areas to an user - all selected and two unchecked')
        self.login()

        self.assertEqual(self.user.userlab_set.count(), 0)

        data1 = {
            'user': self.user.id,
            'areas[]': ['1,0','2,0','3,0','4,1','5,1']
        }
        res = self.client.post( reverse('assign_user_areas'), data=urlencode(data1, True), content_type=ContentType )
        self.assertEqual(res.status_code, 200)
        messages = self.json_messages(res)
        self.assertEqual(messages['status'], 'success')
        self.assertEqual(messages['message'], "Success! test admin's Areas have changed. Please see the following status: <ul class='mb-0'><li>Added: Learning Centre, Bio Lab, Chemistry Lab, Food Lab, Safety Lab</li></ul>")

        userlabs1 = self.user.userlab_set.all()
        self.assertEqual(len(userlabs1), 5)

        labs1 = []
        roles1 = []
        for userlab in userlabs1:
            labs1.append(userlab.lab.name)
            roles1.append(userlab.role)

        self.assertEqual(labs1, ['Learning Centre', 'Bio Lab', 'Chemistry Lab', 'Food Lab', 'Safety Lab'])
        self.assertEqual(roles1, [0, 0, 0, 1, 1])

        data2 = {
            'user': self.user.id,
            'areas[]': ['1,0','3,0','5,1']
        }
        res = self.client.post( reverse('assign_user_areas'), data=urlencode(data2, True), content_type=ContentType )
        self.assertEqual(res.status_code, 200)
        messages = self.json_messages(res)
        self.assertEqual(messages['status'], 'success')
        self.assertEqual(messages['message'], "Success! test admin's Areas have changed. Please see the following status: <ul class='mb-0'><li>Deleted: Bio Lab, Food Lab</li></ul>")

        userlabs2 = self.user.userlab_set.all()
        self.assertEqual(len(userlabs2), 3)

        labs2 = []
        roles2 = []
        for userlab in userlabs2:
            labs2.append(userlab.lab.name)
            roles2.append(userlab.role)

        self.assertEqual(labs2, ['Learning Centre', 'Chemistry Lab', 'Safety Lab'])
        self.assertEqual(roles2, [0, 0, 1])

    def test_assign_areas_to_user_all_selected_all_unchecked(self):
        print('\n- Test: Assign areas to an user - all selected and all unchecked')
        self.login()

        self.assertEqual(self.user.userlab_set.count(), 0)

        data1 = {
            'user': self.user.id,
            'areas[]': ['1,0','2,0','3,0','4,1','5,1']
        }
        res = self.client.post( reverse('assign_user_areas'), data=urlencode(data1, True), content_type=ContentType )
        self.assertEqual(res.status_code, 200)
        messages = self.json_messages(res)
        self.assertEqual(messages['status'], 'success')
        self.assertEqual(messages['message'], "Success! test admin's Areas have changed. Please see the following status: <ul class='mb-0'><li>Added: Learning Centre, Bio Lab, Chemistry Lab, Food Lab, Safety Lab</li></ul>")


        userlabs1 = self.user.userlab_set.all()
        self.assertEqual(len(userlabs1), 5)

        labs1 = []
        roles1 = []
        for userlab in userlabs1:
            labs1.append(userlab.lab.name)
            roles1.append(userlab.role)

        self.assertEqual(labs1, ['Learning Centre', 'Bio Lab', 'Chemistry Lab', 'Food Lab', 'Safety Lab'])
        self.assertEqual(roles1, [0, 0, 0, 1, 1])

        data2 = {
            'user': self.user.id,
            'areas[]': []
        }
        res = self.client.post( reverse('assign_user_areas'), data=urlencode(data2, True), content_type=ContentType )
        self.assertEqual(res.status_code, 200)
        messages = self.json_messages(res)
        self.assertEqual(messages['status'], 'success')
        self.assertEqual(messages['message'], "Success! test admin's all areas have deleted.")

        userlabs2 = self.user.userlab_set.all()
        self.assertEqual(len(userlabs2), 0)

        labs2 = []
        roles2 = []
        for userlab in userlabs2:
            labs2.append(userlab.lab.name)
            roles2.append(userlab.role)

        self.assertEqual(labs2, [])
        self.assertEqual(roles2, [])


    def test_assign_areas_to_user_all_actions(self):
        print('\n- Test: Assign areas to an user - all actions')
        self.login()

        data1 = {
            'user': self.user.id,
            'areas[]': ['1,0','4,1']
        }
        res = self.client.post( reverse('assign_user_areas'), data=urlencode(data1, True), content_type=ContentType )
        self.assertEqual(res.status_code, 200)
        messages = self.json_messages(res)
        self.assertEqual(messages['status'], 'success')
        self.assertEqual(messages['message'], "Success! test admin's Areas have changed. Please see the following status: <ul class='mb-0'><li>Added: Learning Centre, Food Lab</li></ul>")

        userlabs1 = self.user.userlab_set.all()
        self.assertEqual(len(userlabs1), 2)

        labs1 = []
        roles1 = []
        for userlab in userlabs1:
            labs1.append(userlab.lab.name)
            roles1.append(userlab.role)

        self.assertEqual(labs1,  ['Learning Centre', 'Food Lab'])
        self.assertEqual(roles1, [0, 1])


        data2 = {
            'user': self.user.id,
            'areas[]': ['1,1','2,0','3,1']
        }
        res = self.client.post( reverse('assign_user_areas'), data=urlencode(data2, True), content_type=ContentType )
        self.assertEqual(res.status_code, 200)
        messages = self.json_messages(res)
        self.assertEqual(messages['status'], 'success')
        self.assertEqual(messages['message'], "Success! test admin's Areas have changed. Please see the following status: <ul class='mb-0'><li>Changed: Learning Centre</li><li>Added: Bio Lab, Chemistry Lab</li><li>Deleted: Food Lab</li></ul>")

        userlabs2 = self.user.userlab_set.all()
        self.assertEqual(len(userlabs2), 3)

        labs2 = []
        roles2 = []
        for userlab in userlabs2:
            labs2.append(userlab.lab.name)
            roles2.append(userlab.role)

        self.assertEqual(labs2,  ['Learning Centre', 'Bio Lab', 'Chemistry Lab'])
        self.assertEqual(roles2, [1, 0, 1])
