from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from urllib.parse import urlencode

import json

from lfs_lab_cert_tracker.models import UserCert
from lfs_lab_cert_tracker.utils import Api
from lfs_lab_cert_tracker.tests.test_users import LOGIN_URL, ContentType, DATA, USERS, PASSWORD



class TrainingTest(TestCase):
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
        self.login(USERS[2], PASSWORD)

        res = self.client.get(reverse('all_trainings'))
        self.assertEqual(res.status_code, 403)


    def test_check_access_pi(self):
        print('\n- Test: check access - pi')
        self.login(USERS[1], PASSWORD)

        res = self.client.get(reverse('all_trainings'))
        self.assertEqual(res.status_code, 403)


    def test_check_access_admin(self):
        print('\n- Test: check access - admin')
        self.login(USERS[0], PASSWORD)

        res = self.client.get(reverse('all_trainings'))
        self.assertEqual(res.status_code, 200)


    def test_all_trainings(self):
        print('\n- Test: display all trainings')
        self.login()

        res = self.client.get(reverse('all_trainings'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context['trainings']), 26)
        self.assertEqual(res.context['total_trainings'], 26)
        self.assertIsNotNone(res.context['form'])

        training_names = [
            'Accident/Incident Investigation Training Course',
            'Active Shooter Preparedness Workshop',
            'Anesthesia of the Laboratory Rodent',
            'Biological Safety Course',
            'Biology and Husbandry of the Laboratory Rodent'
        ]
        c = 0
        for training in res.context['trainings']:
            self.assertEqual(training.name, training_names[c])
            c += 1
            if c == 5: break


    def test_create_training(self):
        print('\n- Test: create a new training')
        self.login(USERS[0], PASSWORD)

        total_trainings = len(self.api.get_trainings())

        data = {
            'name': 'new training',
            'expiry_in_years': 5
        }

        res = self.client.post(reverse('all_trainings'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! new training created.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('all_trainings'))
        self.assertRedirects(res, res.url)

        self.assertEqual(len(self.api.get_trainings()), total_trainings + 1)

        training = self.api.get_training(data['name'], 'name')

        self.assertEqual(training.name, data['name'])
        self.assertEqual(training.expiry_in_years, data['expiry_in_years'])


    def test_create_training_empty_name(self):
        print('\n- Test: create a new training - empty name')
        self.login(USERS[0], PASSWORD)

        total_trainings = len(self.api.get_trainings())

        data = {
            'expiry_in_years': 5
        }

        res = self.client.post(reverse('all_trainings'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Form is invalid. NAME: Enter a valid name.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('all_trainings'))
        self.assertRedirects(res, res.url)

        self.assertEqual(len(self.api.get_trainings()), total_trainings)


    def test_edit_training_name(self):
        print('\n- Test: edit a training - name')
        self.login(USERS[0], PASSWORD)

        training = self.api.get_training(1)
        data = {
            'name': 'New certificate',
            'expiry_in_years': training.expiry_in_years,
            'training': training.id
        }

        res = self.client.post(reverse('edit_training'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! New certificate training and 6 user training record(s) updated')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('all_trainings'))
        self.assertRedirects(res, res.url)

        training1 = self.api.get_training(data['name'], 'name')
        self.assertEqual(training1.name, data['name'])
        self.assertEqual(training1.expiry_in_years, 0)

    def test_edit_training_expiry_in_years(self):
        print('\n- Test: edit a training - expiry_in_years')
        self.login(USERS[0], PASSWORD)

        training = self.api.get_training(1)
        data = {
            'name': training.name,
            'expiry_in_years': 5,
            'training': training.id
        }

        old_expiry_date = []
        usercerts = UserCert.objects.filter(cert_id=training.id)
        for usercert in usercerts:
            old_expiry_date.append({ "id": usercert.id, "expiry_date": usercert.expiry_date })

        res = self.client.post(reverse('edit_training'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! New Worker Safety Orientation training and 6 user training record(s) updated')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('all_trainings'))
        self.assertRedirects(res, res.url)

        training1 = self.api.get_training(data['name'], 'name')
        self.assertEqual(training1.name, data['name'])
        self.assertEqual(training1.expiry_in_years, 5)

        new_expiry_date = []
        usercerts = UserCert.objects.filter(cert_id=training.id)
        for usercert in usercerts:
            new_expiry_date.append({ "id": usercert.id, "expiry_date": usercert.expiry_date })

        for date1 in old_expiry_date:
            for date2 in new_expiry_date:
                if date1["id"] == date2["id"]:
                    self.assertEqual(date1["expiry_date"].year + 5, date2["expiry_date"].year)


    def test_delete_training(self):
        print('\n- Test: delete a training')
        self.login(USERS[0], PASSWORD)

        total_trainings = len(self.api.get_trainings())

        data = {
            'training': 1
        }

        res = self.client.post(reverse('delete_training'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! New Worker Safety Orientation deleted.')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('all_trainings'))
        self.assertRedirects(res, res.url)

        self.assertEqual(len(self.api.get_trainings()), total_trainings - 1)


    def test_view_user_training_details_by_admin(self):
        print('\n- Test: upload a training - by admin')
        self.login()

        user_id = 11
        training_id = 1

        res = self.client.get(reverse('user_training_details', args=[user_id, training_id]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['app_user'].id, user_id)
        self.assertEqual(res.context['app_user'].username, 'testuser1')
        self.assertEqual(res.context['user_cert'].cert.id, 1)
        self.assertEqual(res.context['user_cert'].cert.name, 'New Worker Safety Orientation')
        self.assertEqual(res.context['viewing'], {})


    def test_view_user_training_details_by_pi(self):
        print('\n- Test: upload a training - by pi')
        self.login(USERS[1], PASSWORD)

        user_id = 11
        training_id = 1

        res = self.client.get(reverse('user_training_details', args=[user_id, training_id]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['app_user'].id, user_id)
        self.assertEqual(res.context['app_user'].username, 'testuser1')
        self.assertEqual(res.context['user_cert'].cert.name, 'New Worker Safety Orientation')
        self.assertEqual(res.context['viewing'], {})


    def test_view_user_training_details_by_wrong_pi(self):
        print('\n- Test: upload a training - by wrong pi')
        self.login('testpi3', PASSWORD)

        res = self.client.get(reverse('user_training_details', args=[12, 1]))
        self.assertEqual(res.status_code, 403)


    def test_view_user_training_details_by_myself(self):
        print('\n- Test: upload a training - by myself')
        self.login(USERS[1], PASSWORD)

        user_id = 11
        training_id = 1

        res = self.client.get(reverse('user_training_details', args=[user_id, training_id]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['app_user'].id, user_id)
        self.assertEqual(res.context['app_user'].username, 'testuser1')
        self.assertEqual(res.context['user_cert'].cert.name, 'New Worker Safety Orientation')
        self.assertEqual(res.context['viewing'], {})
