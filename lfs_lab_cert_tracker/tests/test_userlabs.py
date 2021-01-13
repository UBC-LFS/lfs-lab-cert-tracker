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
