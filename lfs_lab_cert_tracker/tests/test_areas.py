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



class AreaTest(TestCase):
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


    def test_check_access_normal_user(self):
        print('\n- Test: check access - normal user')
        self.login(USERS[2], 'password')

        pi = self.api.get_user(USERS[1], 'username')
        lab_user = self.api.get_user(USERS[2], 'username')

        res = self.client.get(reverse('all_areas'))
        self.assertEqual(res.status_code, 403)

        res = self.client.get(reverse('user_areas', args=[pi.id]))
        self.assertEqual(res.status_code, 403)

        res = self.client.get(reverse('user_areas', args=[lab_user.id]))
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('area_details', args=[1]))
        self.assertEqual(res.status_code, 403)


    def test_check_access_pi(self):
        print('\n- Test: check access - pi')
        self.login(USERS[1], 'password')

        admin = self.api.get_user(USERS[0], 'username')
        pi = self.api.get_user(USERS[1], 'username')
        lab_user = self.api.get_user(USERS[2], 'username')

        res = self.client.get(reverse('all_areas'))
        self.assertEqual(res.status_code, 403)

        res = self.client.get(reverse('user_areas', args=[pi.id]))
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('user_areas', args=[lab_user.id]))
        self.assertEqual(res.status_code, 403)

        res = self.client.get(reverse('area_details', args=[5]))
        self.assertEqual(res.status_code, 403)

        res = self.client.get(reverse('area_details', args=[1]))
        self.assertEqual(res.status_code, 200)


    def test_check_access_admin(self):
        print('\n- Test: check access - admin')
        self.login(USERS[0], 'password')

        admin = self.api.get_user(USERS[0], 'username')
        pi = self.api.get_user(USERS[1], 'username')
        lab_user = self.api.get_user(USERS[2], 'username')

        res = self.client.get(reverse('all_areas'))
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('user_areas', args=[admin.id]))
        self.assertEqual(res.status_code, 200)


        res = self.client.get(reverse('user_areas', args=[pi.id]))
        self.assertEqual(res.status_code, 200)


        res = self.client.get(reverse('user_areas', args=[lab_user.id]))
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('area_details', args=[5]))
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('area_details', args=[1]))
        self.assertEqual(res.status_code, 200)


    def test_create_area(self):
        print('\n- Test: create a new area')
        self.login(USERS[0], 'password')

        total_areas = len(self.api.get_areas())

        data = {
            'name': 'new area'
        }

        res = self.client.post(reverse('all_areas'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! new area created.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('all_areas'))
        self.assertRedirects(res, res.url)

        self.assertEqual(len(self.api.get_areas()), total_areas + 1)

        area = self.api.get_area(data['name'], 'name')
        self.assertEqual(area.name, data['name'])



    def test_edit_area(self):
        print('\n- Test: edit an area')
        self.login(USERS[0], 'password')

        data = {
            'name': 'updated area name',
            'area': 1
        }

        res = self.client.post(reverse('edit_area'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! updated area name updated.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('all_areas'))
        self.assertRedirects(res, res.url)

        area = self.api.get_area(data['name'], 'name')
        self.assertEqual(area.name, data['name'])



    def test_delete_area(self):
        print('\n- Test: delete an area')
        self.login(USERS[0], 'password')

        total_areas = len(self.api.get_areas())

        data = {
            'area': 1
        }

        res = self.client.post(reverse('delete_area'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! Learning Centre deleted.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('all_areas'))
        self.assertRedirects(res, res.url)

        self.assertEqual(len(self.api.get_areas()), total_areas - 1)


    # Trainings in each Area

    def test_add_training_to_area(self):
        print('\n- Test: delete an area')
        self.login(USERS[0], 'password')

        area = self.api.get_area(1)
        total_trainings = area.labcert_set.count()

        data = {
            'lab': 1,
            'cert' : 10
        }

        res = self.client.post(reverse('add_training_area'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! Anesthesia of the Laboratory Rodent added.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('area_details', args=[1]))
        self.assertRedirects(res, res.url)

        area2 = self.api.get_area(1)
        self.assertEqual(area2.labcert_set.count(), total_trainings + 1)



    def test_add_training_to_area_pi(self):
        print('\n- Test: delete an area - pi')
        self.login(USERS[1], 'password')

        area = self.api.get_area(1)
        total_trainings = area.labcert_set.count()

        data = {
            'lab': 1,
            'cert' : 10
        }

        res = self.client.post(reverse('add_training_area'), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 403)


    def test_add_training_to_area_existed(self):
        print('\n- Test: delete an area - existed')
        self.login(USERS[0], 'password')

        data = {
            'lab': 1,
            'cert' : 3
        }

        res = self.client.post(reverse('add_training_area'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Failed to add Training. This training has already existed.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('area_details', args=[1]))
        self.assertRedirects(res, res.url)

    def test_add_training_to_area_invalid(self):
        print('\n- Test: delete an area - invalid')
        self.login(USERS[0], 'password')

        data = {
            'cert' : 3
        }

        res = self.client.post(reverse('add_training_area'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Something went wrong. Area is required.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('all_areas'))
        self.assertRedirects(res, res.url)

    def test_delete_training_in_area(self):
        print('\n- Test: delete a training in an area')
        self.login(USERS[0], 'password')

        area = self.api.get_area(1)
        total_trainings = area.labcert_set.count()

        data = {
            'area': area.id,
            'training': 3
        }

        res = self.client.post(reverse('delete_training_in_area'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! Workplace Violence Prevention Training deleted.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('area_details', args=[area.id]))
        self.assertRedirects(res, res.url)

        area2 = self.api.get_area(1)
        self.assertEqual(area2.labcert_set.count(), total_trainings - 1)


    def test_delete_training_in_area_pi(self):
        print('\n- Test: delete a training in an area - pi')
        self.login(USERS[1], 'password')

        area = self.api.get_area(1)
        total_trainings = area.labcert_set.count()

        data = {
            'area': area.id,
            'training': 3
        }

        res = self.client.post(reverse('delete_training_in_area'), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 403)


    def test_delete_training_in_area_invalid(self):
        print('\n- Test: delete a training in an area - invalid')
        self.login(USERS[0], 'password')

        area = self.api.get_area(1)
        total_trainings = area.labcert_set.count()

        data = {
            'training': 3
        }

        res = self.client.post(reverse('delete_training_in_area'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Something went wrong. Area is required.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('all_areas'))
        self.assertRedirects(res, res.url)


    def test_delete_training_in_area_not_existed(self):
        print('\n- Test: delete a training in an area - not existed')
        self.login(USERS[0], 'password')

        area = self.api.get_area(1)
        total_trainings = area.labcert_set.count()

        data = {
            'area': 1,
            'training': 10
        }

        res = self.client.post(reverse('delete_training_in_area'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Anesthesia of the Laboratory Rodent does not exist in this area.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('area_details', args=[area.id]))
        self.assertRedirects(res, res.url)


    def test_add_user_to_area(self):
        print('\n- Test: add a user to an area')
        self.login(USERS[0], 'password')

        area = self.api.get_area(1)
        total_users = area.userlab_set.count()

        data = {
            'user': 'testuser2',
            'lab': area.id,
            'role': 0
        }

        res = self.client.post(reverse('area_details', args=[area.id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Warning! Added test user2 successfully, but failed to send an email. (email address is invalid)')
        self.assertEqual(res.url, reverse('area_details', args=[area.id]))
        self.assertRedirects(res, res.url)

        area2 = self.api.get_area(1)
        self.assertEqual(area2.userlab_set.count(), total_users + 1)

        userlab = area2.userlab_set.filter(user__username=data['user']).first()
        self.assertEqual(userlab.user.username, data['user'])
        self.assertEqual(userlab.role, data['role'])


    def test_add_user_to_area_pi(self):
        print('\n- Test: add a user to an area - pi')
        self.login(USERS[1], 'password')

        area = self.api.get_area(1)
        total_users = area.userlab_set.count()

        data = {
            'user': 'testuser2',
            'lab': area.id,
            'role': 0
        }

        res = self.client.post(reverse('area_details', args=[area.id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Warning! Added test user2 successfully, but failed to send an email. (email address is invalid)')
        self.assertEqual(res.url, reverse('area_details', args=[area.id]))
        self.assertRedirects(res, res.url)

        area2 = self.api.get_area(1)
        self.assertEqual(area2.userlab_set.count(), total_users + 1)

        userlab = area2.userlab_set.filter(user__username=data['user']).first()
        self.assertEqual(userlab.user.username, data['user'])
        self.assertEqual(userlab.role, data['role'])



    def test_add_user_to_area_existing_username(self):
        print('\n- Test: add a user to an area - existing username')
        self.login(USERS[0], 'password')

        area = self.api.get_area(1)
        total_users = area.userlab_set.count()

        data = {
            'user': 'testuser1',
            'lab': area.id,
            'role': 0
        }

        res = self.client.post(reverse('area_details', args=[area.id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Failed to add testuser1. CWL already exists in this area.')
        self.assertEqual(res.url, reverse('area_details', args=[area.id]))
        self.assertRedirects(res, res.url)


    def test_add_user_to_area_none_username(self):
        print('\n- Test: add a user to an area - none username')
        self.login(USERS[0], 'password')

        area = self.api.get_area(1)
        total_users = area.userlab_set.count()

        data = {
            'user': 'testuser2000',
            'lab': area.id,
            'role': 0
        }

        res = self.client.post(reverse('area_details', args=[area.id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Failed to add testuser2000. CWL does not exist in TRMS. Please go to a Users page then create the user by inputting the details before adding the user in the area.')
        self.assertEqual(res.url, reverse('area_details', args=[area.id]))
        self.assertRedirects(res, res.url)


    def test_switch_role_user_to_pi(self):
        print('\n- Test: switch a role from user to pi')
        self.login(USERS[0], 'password')

        area = self.api.get_area(1)
        user = self.api.get_user(11)

        userlab = user.userlab_set.filter(lab__id=area.id).first()
        self.assertEqual(userlab.role, 0)

        data = {
            'user': user.id,
            'area': area.id
        }

        res = self.client.post(reverse('switch_user_role_in_area', args=[area.id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! test user1 is now a Supervisor.')
        self.assertEqual(res.url, reverse('area_details', args=[area.id]))
        self.assertRedirects(res, res.url)

        user2 = self.api.get_user(11)
        userlab2 = user2.userlab_set.filter(lab__id=area.id).first()
        self.assertEqual(userlab2.role, 1)


    def test_switch_role_user_to_pi(self):
        print('\n- Test: switch a role from pi to user')
        self.login(USERS[0], 'password')

        area = self.api.get_area(1)
        user = self.api.get_user(4)

        userlab = user.userlab_set.filter(lab__id=area.id).first()
        self.assertEqual(userlab.role, 1)

        data = {
            'user': user.id,
            'area': area.id
        }

        res = self.client.post(reverse('switch_user_role_in_area', args=[area.id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! test pi1 is now a User.')
        self.assertEqual(res.url, reverse('area_details', args=[area.id]))
        self.assertRedirects(res, res.url)

        user2 = self.api.get_user(4)

        userlab2 = user2.userlab_set.filter(lab__id=area.id).first()
        self.assertEqual(userlab2.role, 0)



    def test_switch_role_user_to_pi_by_pi(self):
        print('\n- Test: switch a role from user to pi - by pi')
        self.login(USERS[1], 'password')

        area = self.api.get_area(1)
        user = self.api.get_user(11)

        userlab = user.userlab_set.filter(lab__id=area.id).first()
        self.assertEqual(userlab.role, 0)

        data = {
            'user': user.id,
            'area': area.id
        }

        res = self.client.post(reverse('switch_user_role_in_area', args=[area.id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! test user1 is now a Supervisor.')
        self.assertEqual(res.url, reverse('area_details', args=[area.id]))
        self.assertRedirects(res, res.url)

        user2 = self.api.get_user(11)
        userlab2 = user2.userlab_set.filter(lab__id=area.id).first()
        self.assertEqual(userlab2.role, 1)


    def test_switch_role_user_to_pi_by_pi(self):
        print('\n- Test: switch a role from pi to user - by pi')
        self.login(USERS[1], 'password')

        area = self.api.get_area(1)
        user = self.api.get_user(5)

        userlab = user.userlab_set.filter(lab__id=area.id).first()
        self.assertEqual(userlab.role, 1)

        data = {
            'user': user.id,
            'area': area.id
        }

        res = self.client.post(reverse('switch_user_role_in_area', args=[area.id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! test pi2 is now a User.')
        self.assertEqual(res.url, reverse('area_details', args=[area.id]))
        self.assertRedirects(res, res.url)

        user2 = self.api.get_user(5)

        userlab2 = user2.userlab_set.filter(lab__id=area.id).first()
        self.assertEqual(userlab2.role, 0)


    def test_switch_role_user_to_pi_by_wrong_pi(self):
        print('\n- Test: switch a role from user to pi - by wrong pi')
        self.login(USERS[1], 'password')

        area = self.api.get_area(2)
        user = self.api.get_user(11)

        userlab = user.userlab_set.filter(lab__id=area.id).first()
        self.assertEqual(userlab.role, 0)

        data = {
            'user': user.id,
            'area': area.id
        }

        res = self.client.post(reverse('switch_user_role_in_area', args=[area.id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 403)


    def test_switch_role_missing_user(self):
        print('\n- Test: switch a role - missing user')
        self.login(USERS[0], 'password')

        area = self.api.get_area(1)

        data = {
            'area': area.id
        }

        res = self.client.post(reverse('switch_user_role_in_area', args=[area.id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Something went wrong. User is required.')
        self.assertEqual(res.url, reverse('area_details', args=[area.id]))
        self.assertRedirects(res, res.url)


    def test_switch_role_invalid_user(self):
        print('\n- Test: switch a role - invalid user')
        self.login(USERS[0], 'password')

        area = self.api.get_area(1)

        data = {
            'user': 2000,
            'area': area.id
        }

        res = self.client.post(reverse('switch_user_role_in_area', args=[area.id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 404)


    def test_switch_role_missing_area(self):
        print('\n- Test: switch a role - missing area')
        self.login(USERS[0], 'password')

        area = self.api.get_area(1)
        user = self.api.get_user(20)

        data = {
            'user': user.id
        }

        res = self.client.post(reverse('switch_user_role_in_area', args=[area.id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Something went wrong. Area is required.')
        self.assertEqual(res.url, reverse('all_areas'))
        self.assertRedirects(res, res.url)


    def test_switch_role_invalid_area(self):
        print('\n- Test: switch a role - invalid area')
        self.login(USERS[0], 'password')

        user = self.api.get_user(20)

        data = {
            'user': user.id,
            'area': 100
        }

        res = self.client.post(reverse('switch_user_role_in_area', args=[100]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 404)



    # delete_user_in_area

    def test_delete_user_in_area(self):
        print('\n- Test: delete a user in an area')
        self.login(USERS[0], 'password')

        area = self.api.get_area(1)
        total_users = area.userlab_set.count()

        user = self.api.get_user(15)

        data = {
            'user': user.id,
            'area': area.id
        }

        res = self.client.post(reverse('delete_user_in_area', args=[area.id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! test user5 deleted.')
        self.assertEqual(res.url, reverse('area_details', args=[area.id]))
        self.assertRedirects(res, res.url)



    def test_delete_user_in_area_by_pi(self):
        print('\n- Test: delete a user in an area - by pi')
        self.login(USERS[1], 'password')

        area = self.api.get_area(1)
        total_users = area.userlab_set.count()

        user = self.api.get_user(15)

        data = {
            'user': user.id,
            'area': area.id
        }

        res = self.client.post(reverse('delete_user_in_area', args=[area.id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! test user5 deleted.')
        self.assertEqual(res.url, reverse('area_details', args=[area.id]))
        self.assertRedirects(res, res.url)


    def test_delete_user_in_area_by_pi(self):
        print('\n- Test: delete a user in an area - by pi')
        self.login(USERS[1], 'password')

        area = self.api.get_area(2)
        total_users = area.userlab_set.count()

        user = self.api.get_user(20)

        data = {
            'user': user.id,
            'area': area.id
        }

        res = self.client.post(reverse('delete_user_in_area', args=[area.id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 403)


    def test_delete_user_in_area_missing_user(self):
        print('\n- Test: delete a user in an area - missing user')
        self.login(USERS[0], 'password')

        area = self.api.get_area(1)

        data = {
            'area': area.id
        }

        res = self.client.post(reverse('delete_user_in_area', args=[area.id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Something went wrong. User is required.')
        self.assertEqual(res.url, reverse('area_details', args=[area.id]))
        self.assertRedirects(res, res.url)



    def test_delete_user_in_area_invalid_user(self):
        print('\n- Test: delete a user in an area - invalid user')
        self.login(USERS[0], 'password')

        area = self.api.get_area(1)

        data = {
            'user': 2000,
            'area': area.id
        }

        res = self.client.post(reverse('delete_user_in_area', args=[area.id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 404)


    def test_delete_user_in_area_missing_area(self):
        print('\n- Test: delete a user in an area - missing area')
        self.login(USERS[0], 'password')

        area = self.api.get_area(1)
        user = self.api.get_user(20)

        data = {
            'user': user.id
        }

        res = self.client.post(reverse('delete_user_in_area', args=[area.id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Something went wrong. Area is required.')
        self.assertEqual(res.url, reverse('all_areas'))
        self.assertRedirects(res, res.url)


    def test_delete_user_in_area_invalid_area(self):
        print('\n- Test: delete a user in an area - invalid area')
        self.login(USERS[0], 'password')

        user = self.api.get_user(20)

        data = {
            'user': user.id,
            'area': 100
        }

        res = self.client.post(reverse('delete_user_in_area', args=[100]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 404)
