from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from urllib.parse import urlencode

import json
from datetime import datetime

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


ALL_USERS_QUERY = '?page=1&q=user'

ALL_USERS_NEXT = '?next=/users/all/' + ALL_USERS_QUERY

class UserTest(TestCase):
    fixtures = DATA

    @classmethod
    def setUpTestData(cls):
        cls.api = Api()
        cls.user = cls.api.get_user(USERS[0], 'username')

    def login(self, username=None, password=None):
        if username and password:
            self.client.post(LOGIN_URL, data={'username': username, 'password': password})
        else:
            self.client.post(LOGIN_URL, data={'username': self.user.username, 'password': PASSWORD})

    def messages(self, res):
        return [m.message for m in get_messages(res.wsgi_request)]

    def json_messages(self, res):
        return json.loads( res.content.decode('utf-8') )

    def test_check_access_normal_user(self):
        print('\n- Test: check access - normal user')
        self.login(USERS[2], 'password')

        lab_user = self.api.get_user(USERS[2], 'username')

        res = self.client.get(reverse('all_users')) # all users
        self.assertEqual(res.status_code, 403)


        # user details

        res = self.client.get(reverse('user_details', args=[2]) + '?next=/area/all/?page=1&q=user') # anonymous
        self.assertEqual(res.status_code, 403)

        res = self.client.get(reverse('user_details', args=[lab_user.id]) + '?next=/users/all/?page=1&q=user') # myself
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('user_details', args=[lab_user.id]) + '?next=/areas/1/') # myself from area
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('new_user')) # new user
        self.assertEqual(res.status_code, 403)

        res = self.client.get(reverse('user_report_missing_trainings')) # user report - missing trainings
        self.assertEqual(res.status_code, 403)


    def test_check_access_pi(self):
        print('\n- Test: check access - pi')
        self.login(USERS[1], 'password')

        pi = self.api.get_user(USERS[1], 'username')
        lab_user = self.api.get_user(USERS[2], 'username')

        res = self.client.get(reverse('all_users')) # all users
        self.assertEqual(res.status_code, 403)


        # user details

        res = self.client.get(reverse('user_details', args=[2]) + '?next=/users/all/?page=1&q=user') # anonymous
        self.assertEqual(res.status_code, 403)

        res = self.client.get(reverse('user_details', args=[lab_user.id]) + '?next=/users/all/?page=1&q=user') # lab user
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('user_details', args=[pi.id]) + '?next=/users/all/?page=1&q=user') # lab user
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('user_details', args=[pi.id]) + '?next=/areas/1/') # myself
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('new_user')) # new user
        self.assertEqual(res.status_code, 403)

        res = self.client.get(reverse('user_report_missing_trainings')) # user report - missing trainings
        self.assertEqual(res.status_code, 403)


    def test_check_access_admin(self):
        print('\n- Test: check access - admin')
        self.login()

        admin = self.api.get_user(USERS[0], 'username')
        pi = self.api.get_user(USERS[1], 'username')
        lab_user = self.api.get_user(USERS[2], 'username')

        # all users

        res = self.client.get(reverse('all_users') + ALL_USERS_QUERY)
        self.assertEqual(res.status_code, 200)


        # user details

        res = self.client.get(reverse('user_details', args=[2]) + '?next=/users/all/?page=1&q=user&u=2') # anonymous
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('user_details', args=[lab_user.id]) + '?next=/users/all/?page=1&q=user') # lab user
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('user_details', args=[pi.id]) + '?next=/users/all/?page=1&q=user') # pi
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('user_details', args=[admin.id]) + '?next=/users/all/?page=1&q=user') # admin
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('user_details', args=[admin.id]) + '?next=/areas/1/') # myself from work area
        self.assertEqual(res.status_code, 200)


        res = self.client.get(reverse('new_user')) # new user
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('user_report_missing_trainings')) # user report - missing trainings
        self.assertEqual(res.status_code, 200)




    def test_get_users(self):
        print('\n- Test: show users')
        self.login()

        res = self.client.get(reverse('all_users') + ALL_USERS_QUERY)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context['users']), 21)
        self.assertEqual(res.context['total_users'], 21)
        self.assertEqual(len(res.context['areas']), 5)
        self.assertEqual(res.context['roles'], {'LAB_USER': 0, 'PI': 1})

    def test_edit_user_duplicated_username(self):
        print('\n- Test: edit an user basic information - duplicated information')
        self.login()

        user = self.api.get_user(USERS[2], 'username')
        EMAIL = 'test.user1@example.com'

        data = {
            'username': USERS[0],
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': EMAIL,
            'user': user.id,
            'next': reverse('all_users') + ALL_USERS_QUERY
        }
        res = self.client.post(reverse('all_users'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Form is invalid. USERNAME: A user with that username already exists.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('all_users') + ALL_USERS_QUERY)
        self.assertRedirects(res, res.url)

    def test_edit_user_invalid_email(self):
        print('\n- Test: edit an user basic information - invalid email')
        self.login()

        user = self.api.get_user(USERS[2], 'username')
        data = {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'user': user.id,
            'next': reverse('all_users') + ALL_USERS_QUERY
        }
        res = self.client.post(reverse('all_users'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Form is invalid. EMAIL: Enter a valid email address.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('all_users') + ALL_USERS_QUERY)
        self.assertRedirects(res, res.url)


    def test_edit_user_firstname_long(self):
        print('\n- Test: edit an user basic information - firstname long')
        self.login()

        user = self.api.get_user(USERS[2], 'username')
        EMAIL = 'test.user1@example.com'

        data = {
            'username': user.username,
            'first_name': 'abcdefgijlabcdefgijlabcdefgijlu',
            'last_name': user.last_name,
            'email': EMAIL,
            'user': user.id,
            'next': reverse('all_users') + ALL_USERS_QUERY
        }
        res = self.client.post(reverse('all_users') + ALL_USERS_QUERY, data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Form is invalid. FIRST NAME: Ensure this value has at most 30 characters (it has 31).')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('all_users') + ALL_USERS_QUERY)
        self.assertRedirects(res, res.url)


    def test_edit_user_valid(self):
        print('\n- Test: edit an user basic information - valid')
        self.login()

        user = self.api.get_user(USERS[2], 'username')
        EMAIL = 'test.user1@example.com'

        data = {
            'username': 'edited' + user.username,
            'first_name': 'edited' + user.first_name,
            'last_name': 'edited' + user.last_name,
            'email': 'edited' + EMAIL,
            'user': user.id,
            'next': reverse('all_users') + ALL_USERS_QUERY
        }
        res = self.client.post(reverse('all_users') + ALL_USERS_QUERY, data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertTrue('Success' in messages[0])
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('all_users') + ALL_USERS_QUERY)
        self.assertRedirects(res, res.url)

        user = self.api.get_user(data['username'], 'username')
        self.assertEqual(user.id, data['user'])
        self.assertEqual(user.username, data['username'])
        self.assertEqual(user.first_name, data['first_name'])
        self.assertEqual(user.last_name, data['last_name'])
        self.assertEqual(user.email, data['email'])



    def test_grant_admin(self):
        print('\n- Test: grant admin')
        self.login()

        user = self.api.get_user(USERS[2], 'username')
        self.assertFalse(user.is_superuser)

        data = {
            'user': user.id,
            'next': '/users/all/' + ALL_USERS_QUERY
        }

        res = self.client.post(reverse('switch_admin'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! Granted administrator privileges to test user1.')

        user = self.api.get_user(USERS[2], 'username')
        self.assertTrue(user.is_superuser)

    def test_revoke_admin(self):
        print('\n- Test: remove admin')
        self.login()

        user = self.api.get_user('testadmin2', 'username')
        self.assertTrue(user.is_superuser)

        data = {
            'user': user.id,
            'next': '/users/all/'
        }

        res = self.client.post(reverse('switch_admin'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! Revoked administrator privileges of test admin2.')

        user = self.api.get_user('testadmin2', 'username')
        self.assertFalse(user.is_superuser)



    def test_inactive_user(self):
        print('\n- Test: inactive user')
        self.login()

        user = self.api.get_user(USERS[2], 'username')
        self.assertTrue(user.is_active)

        data = {
            'user': user.id,
            'next': '/users/all/' + ALL_USERS_QUERY
        }

        res = self.client.post(reverse('switch_inactive'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! test user1 is now INACTIVE.')

        user = self.api.get_user(USERS[2], 'username')
        self.assertFalse(user.is_active)
        self.assertEqual(user.userinactive_set.first().inactive_date, datetime.now().date())


    def test_active_user(self):
        print('\n- Test: active user')
        self.login()

        user = self.api.get_user(USERS[2], 'username')
        self.assertTrue(user.is_active)

        data1 = {
            'user': user.id,
            'next': '/users/all/' + ALL_USERS_QUERY
        }

        res = self.client.post(reverse('switch_inactive'), data=urlencode(data1), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! test user1 is now INACTIVE.')

        user = self.api.get_user(USERS[2], 'username')
        self.assertFalse(user.is_active)
        self.assertEqual(user.userinactive_set.first().inactive_date, datetime.now().date())

        data2 = {
            'user': user.id,
            'next': '/users/all/' + ALL_USERS_QUERY
        }

        res2 = self.client.post(reverse('switch_inactive'), data=urlencode(data2), content_type=ContentType)
        messages2 = self.messages(res2)
        self.assertEqual(messages2[1], 'Success! test user1 is now ACTIVE.')

        user = self.api.get_user(USERS[2], 'username')
        self.assertTrue(user.is_active)
        self.assertEqual(user.userinactive_set.count(), 0)

    def test_delete_user(self):
        print('\n- Test: delete a user')
        self.login()

        total_users = len(self.api.get_users())

        user = self.api.get_user(USERS[2], 'username')
        self.assertTrue(user.is_active)

        data = {
            'user': user.id,
            'next': '/users/all/' + ALL_USERS_QUERY
        }

        res = self.client.post(reverse('delete_user'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! test user1 deleted.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('all_users') + ALL_USERS_QUERY)
        self.assertRedirects(res, res.url)

        self.assertEqual(len(self.api.get_users()), total_users - 1)

        # TODO
        # check inactive, training records, areas



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
        user = self.api.get_user(11)
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

        user = self.api.get_user(11)
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

        user = self.api.get_user(11)
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


    def test_user_details(self):
        print('\n- Test: show user details')
        self.login()

        user = self.api.get_user(USERS[2], 'username')

        res = self.client.get(reverse('user_details', args=[user.id]) + ALL_USERS_NEXT + '&u=' + str(user.id))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['app_user'].id, user.id)
        self.assertEqual(res.context['app_user'].username, user.username)
        self.assertEqual(res.context['viewing'], {'page': 'all_users', 'query': 'page=1&q=user&u=11'})

        # TODO
        # different next path


    def test_user_report_missing_trainings(self):
        print('\n- Test: Get a user report for missing trainings')
        self.login()

        res = self.client.get(reverse('user_report_missing_trainings'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['total_users'], 7)

        users = ['testpi1', 'testpi2', 'testpi3', 'testuser1', 'testuser10', 'testuser3', 'testuser5']
        c = 0
        for user in res.context['users']:
            self.assertEqual(user.username, users[c])
            c += 1


    def test_create_user(self):
        print('\n- Test: create a new user')
        self.login()

        data = {
            'username': 'testuser500',
            'last_name': 'test',
            'first_name': 'user500',
            'email': 'test.user500@example.com'
        }

        res = self.client.post(reverse('new_user'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! testuser500 created.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('new_user'))
        self.assertRedirects(res, res.url)


    def test_create_user_long_first_name(self):
        print('\n- Test: create a new user - long first name')
        self.login()

        data = {
            'username': 'testuser500',
            'last_name': 'test',
            'first_name': 'user500000000000000000000000000',
            'email': 'test.user500@example.com'
        }

        res = self.client.post(reverse('new_user'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Form is invalid. FIRST NAME: Ensure this value has at most 30 characters (it has 31).')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('new_user'))
        self.assertRedirects(res, res.url)


    def test_create_user_invalid_email(self):
        print('\n- Test: create a new user - invalid email')
        self.login()

        data = {
            'username': 'testuser500',
            'last_name': 'test',
            'first_name': 'user500',
            'email': 'abc'
        }

        res = self.client.post(reverse('new_user'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Form is invalid. EMAIL: Enter a valid email address.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('new_user'))
        self.assertRedirects(res, res.url)


    def test_create_user_missed_username(self):
        print('\n- Test: create a new user - missed username')
        self.login()

        data = {
            'last_name': 'test',
            'first_name': 'user500',
            'email': 'test.user500@example.com'
        }

        res = self.client.post(reverse('new_user'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Form is invalid. USERNAME: Enter a valid username.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('new_user'))
        self.assertRedirects(res, res.url)


    def test_create_user_duplicated_username(self):
        print('\n- Test: create a new user - duplicated username')
        self.login()

        data = {
            'username': USERS[2],
            'last_name': 'test',
            'first_name': 'user500',
            'email': 'test.user500@example.com'
        }

        res = self.client.post(reverse('new_user'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Form is invalid. USERNAME: A user with that username already exists.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('new_user'))
        self.assertRedirects(res, res.url)
