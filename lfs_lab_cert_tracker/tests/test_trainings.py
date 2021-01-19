import os
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from urllib.parse import urlencode
from django.core.files.uploadedfile import SimpleUploadedFile

import json
from datetime import datetime as dt
import datetime

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


class TrainingTest(TestCase):
    fixtures = DATA

    @classmethod
    def setUpTestData(cls):
        cls.api = Api()
        cls.user = cls.api.get_user(USERS[0], 'username')
        cls.testing_image = os.path.join(settings.BASE_DIR, 'lfs_lab_cert_tracker', 'tests', 'files', 'joss-woodhead-3wFRlwS91yk-unsplash.jpg')
        cls.testing_image2 = os.path.join(settings.BASE_DIR, 'lfs_lab_cert_tracker', 'tests', 'files', 'karsten-wurth-9qvZSH_NOQs-unsplash.jpg')

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


    def test_edit_training(self):
        print('\n- Test: edit a training')
        self.login(USERS[0], PASSWORD)

        data = {
            'name': 'updated training name',
            'training': 1
        }

        res = self.client.post(reverse('edit_training'), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! updated training name updated')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('all_trainings'))
        self.assertRedirects(res, res.url)

        training = self.api.get_training(data['name'], 'name')
        self.assertEqual(training.name, data['name'])
        self.assertEqual(training.expiry_in_years, 0)


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


    def test_view_user_trainings_by_admin(self):
        print("\n- Test: view user's trainings - by admin")
        self.login(USERS[0], PASSWORD)

        user_id = 11

        res = self.client.get(reverse('user_trainings', args=[user_id]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['app_user'].id, user_id)
        self.assertEqual(len(res.context['user_cert_list']), 6)

        self.assertEqual(res.context['user_cert_list'][0]['id'], 1)
        self.assertEqual(res.context['user_cert_list'][0]['user'], 11)
        self.assertEqual(res.context['user_cert_list'][0]['cert'], 1)
        self.assertIsNotNone(res.context['user_cert_list'][0]['cert_file'])
        self.assertEqual(res.context['user_cert_list'][0]['uploaded_date'], datetime.date(2018, 6, 10))
        self.assertEqual(res.context['user_cert_list'][0]['completion_date'], datetime.date(2014, 8, 15))
        self.assertEqual(res.context['user_cert_list'][0]['expiry_date'], datetime.date(2014, 8, 15))
        self.assertEqual(res.context['user_cert_list'][0]['name'], 'New Worker Safety Orientation')
        self.assertEqual(res.context['user_cert_list'][0]['expiry_in_years'], 0)

        self.assertEqual(res.context['user_cert_list'][1]['id'], 3)
        self.assertEqual(res.context['user_cert_list'][1]['user'], 11)
        self.assertEqual(res.context['user_cert_list'][1]['cert'], 3)
        self.assertIsNotNone(res.context['user_cert_list'][1]['cert_file'])
        self.assertEqual(res.context['user_cert_list'][1]['uploaded_date'], datetime.date(2018, 6, 10))
        self.assertEqual(res.context['user_cert_list'][1]['completion_date'], datetime.date(2014, 7, 10))
        self.assertEqual(res.context['user_cert_list'][1]['expiry_date'], datetime.date(2014, 7, 10))
        self.assertEqual(res.context['user_cert_list'][1]['name'], 'Workplace Violence Prevention Training')
        self.assertEqual(res.context['user_cert_list'][1]['expiry_in_years'], 0)

        self.assertEqual(res.context['user_cert_list'][2]['id'], 20)
        self.assertEqual(res.context['user_cert_list'][2]['user'], 11)
        self.assertEqual(res.context['user_cert_list'][2]['cert'], 20)
        self.assertIsNotNone(res.context['user_cert_list'][2]['cert_file'])
        self.assertEqual(res.context['user_cert_list'][2]['uploaded_date'], datetime.date(2018, 6, 10))
        self.assertEqual(res.context['user_cert_list'][2]['completion_date'], datetime.date(2014, 7, 14))
        self.assertEqual(res.context['user_cert_list'][2]['expiry_date'], datetime.date(2019, 7, 14))
        self.assertEqual(res.context['user_cert_list'][2]['name'], 'Biosafety for Permit Holders')
        self.assertEqual(res.context['user_cert_list'][2]['expiry_in_years'], 5)

        self.assertEqual(res.context['user_cert_list'][3]['id'], 23)
        self.assertEqual(res.context['user_cert_list'][3]['user'], 11)
        self.assertEqual(res.context['user_cert_list'][3]['cert'], 23)
        self.assertIsNotNone(res.context['user_cert_list'][3]['cert_file'])
        self.assertEqual(res.context['user_cert_list'][3]['uploaded_date'], datetime.date(2018, 6, 10))
        self.assertEqual(res.context['user_cert_list'][3]['completion_date'], datetime.date(2017, 7, 13))
        self.assertEqual(res.context['user_cert_list'][3]['expiry_date'], datetime.date(2019, 7, 13))
        self.assertEqual(res.context['user_cert_list'][3]['name'], 'Transportation of Dangerous Goods Class 6.2 (Biological materials) Shipping Course for air')
        self.assertEqual(res.context['user_cert_list'][3]['expiry_in_years'], 2)

        self.assertEqual(res.context['user_cert_list'][4]['id'], 16)
        self.assertEqual(res.context['user_cert_list'][4]['user'], 11)
        self.assertEqual(res.context['user_cert_list'][4]['cert'], 16)
        self.assertIsNotNone(res.context['user_cert_list'][4]['cert_file'])
        self.assertEqual(res.context['user_cert_list'][4]['uploaded_date'], datetime.date(2020, 1, 10))
        self.assertEqual(res.context['user_cert_list'][4]['completion_date'], datetime.date(2014, 10, 1))
        self.assertEqual(res.context['user_cert_list'][4]['expiry_date'], datetime.date(2019, 10, 1))
        self.assertEqual(res.context['user_cert_list'][4]['name'], 'Biological Safety Course')
        self.assertEqual(res.context['user_cert_list'][4]['expiry_in_years'], 5)

        self.assertEqual(res.context['user_cert_list'][5]['id'], 22)
        self.assertEqual(res.context['user_cert_list'][5]['user'], 11)
        self.assertEqual(res.context['user_cert_list'][5]['cert'], 22)
        self.assertIsNotNone(res.context['user_cert_list'][5]['cert_file'])
        self.assertEqual(res.context['user_cert_list'][5]['uploaded_date'], datetime.date(2020, 1, 10))
        self.assertEqual(res.context['user_cert_list'][5]['completion_date'], datetime.date(2016, 10, 1))
        self.assertEqual(res.context['user_cert_list'][5]['expiry_date'], datetime.date(2019, 10, 1))
        self.assertEqual(res.context['user_cert_list'][5]['name'], 'Transportation of Dangerous Goods Class 7 (Radioactivity) Receiving Course for ground')
        self.assertEqual(res.context['user_cert_list'][5]['expiry_in_years'], 3)

        self.assertEqual(res.context['missing_cert_list'], [{'id': 2, 'name': 'Preventing and Addressing Workplace Bullying and Harassment Training', 'expiry_in_years': 0}, {'id': 5, 'name': 'Privacy and Information Security Fundamentals Training', 'expiry_in_years': 0}, {'id': 15, 'name': 'Chemical Safety Course', 'expiry_in_years': 5}])
        self.assertEqual(res.context['expired_cert_list'], [{'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_in_years': 5}, {'id': 23, 'name': 'Transportation of Dangerous Goods Class 6.2 (Biological materials) Shipping Course for air', 'expiry_in_years': 2}, {'id': 16, 'name': 'Biological Safety Course', 'expiry_in_years': 5}, {'id': 22, 'name': 'Transportation of Dangerous Goods Class 7 (Radioactivity) Receiving Course for ground', 'expiry_in_years': 3}])
        self.assertIsNotNone(res.context['form'])
        self.assertIsNotNone(res.context['viewing'], {})


    def test_upload_training_by_admin(self):
        print('\n- Test: upload a training - by admin')
        self.login(USERS[0], PASSWORD)

        user_id = 11
        training_id = 2

        user = self.api.get_user(user_id)
        self.assertFalse(user.usercert_set.filter(cert_id=training_id).exists())

        data = {
            'user': user_id,
            'cert': 2,
            'cert_file': SimpleUploadedFile(name='joss-woodhead-3wFRlwS91yk-unsplash.jpg', content=open(self.testing_image, 'rb').read(), content_type='image/jpeg'),
            'completion_date_year': 2020,
            'completion_date_month': 1,
            'completion_date_day': 15
        }

        res = self.client.post(reverse('user_trainings', args=[user_id]), data=data, format='multipart')
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! Preventing and Addressing Workplace Bullying and Harassment Training added.')
        self.assertEqual(res.url, reverse('user_trainings', args=[user.id]))
        self.assertRedirects(res, res.url)


        user2 = self.api.get_user(user_id)
        training = user2.usercert_set.filter(cert_id=training_id)
        self.assertTrue(training.exists())
        self.assertEqual(training.first().cert.name, 'Preventing and Addressing Workplace Bullying and Harassment Training')
        self.assertEqual(training.first().cert_file.name, 'users/11/certificates/2/joss-woodhead-3wFRlwS91yk-unsplash.jpg')
        training.delete()


    def test_view_user_trainings_by_pi(self):
        print("\n- Test: view user's trainings - by pi")
        self.login(USERS[1], PASSWORD)

        user_id = 11

        res = self.client.get(reverse('user_trainings', args=[user_id]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['app_user'].id, user_id)
        self.assertEqual(len(res.context['user_cert_list']), 6)

        self.assertEqual(res.context['user_cert_list'][0]['id'], 1)
        self.assertEqual(res.context['user_cert_list'][0]['user'], 11)
        self.assertEqual(res.context['user_cert_list'][0]['cert'], 1)
        self.assertIsNotNone(res.context['user_cert_list'][0]['cert_file'])
        self.assertEqual(res.context['user_cert_list'][0]['uploaded_date'], datetime.date(2018, 6, 10))
        self.assertEqual(res.context['user_cert_list'][0]['completion_date'], datetime.date(2014, 8, 15))
        self.assertEqual(res.context['user_cert_list'][0]['expiry_date'], datetime.date(2014, 8, 15))
        self.assertEqual(res.context['user_cert_list'][0]['name'], 'New Worker Safety Orientation')
        self.assertEqual(res.context['user_cert_list'][0]['expiry_in_years'], 0)

        self.assertEqual(res.context['user_cert_list'][1]['id'], 3)
        self.assertEqual(res.context['user_cert_list'][1]['user'], 11)
        self.assertEqual(res.context['user_cert_list'][1]['cert'], 3)
        self.assertIsNotNone(res.context['user_cert_list'][1]['cert_file'])
        self.assertEqual(res.context['user_cert_list'][1]['uploaded_date'], datetime.date(2018, 6, 10))
        self.assertEqual(res.context['user_cert_list'][1]['completion_date'], datetime.date(2014, 7, 10))
        self.assertEqual(res.context['user_cert_list'][1]['expiry_date'], datetime.date(2014, 7, 10))
        self.assertEqual(res.context['user_cert_list'][1]['name'], 'Workplace Violence Prevention Training')
        self.assertEqual(res.context['user_cert_list'][1]['expiry_in_years'], 0)

        self.assertEqual(res.context['user_cert_list'][2]['id'], 20)
        self.assertEqual(res.context['user_cert_list'][2]['user'], 11)
        self.assertEqual(res.context['user_cert_list'][2]['cert'], 20)
        self.assertIsNotNone(res.context['user_cert_list'][2]['cert_file'])
        self.assertEqual(res.context['user_cert_list'][2]['uploaded_date'], datetime.date(2018, 6, 10))
        self.assertEqual(res.context['user_cert_list'][2]['completion_date'], datetime.date(2014, 7, 14))
        self.assertEqual(res.context['user_cert_list'][2]['expiry_date'], datetime.date(2019, 7, 14))
        self.assertEqual(res.context['user_cert_list'][2]['name'], 'Biosafety for Permit Holders')
        self.assertEqual(res.context['user_cert_list'][2]['expiry_in_years'], 5)

        self.assertEqual(res.context['user_cert_list'][3]['id'], 23)
        self.assertEqual(res.context['user_cert_list'][3]['user'], 11)
        self.assertEqual(res.context['user_cert_list'][3]['cert'], 23)
        self.assertIsNotNone(res.context['user_cert_list'][3]['cert_file'])
        self.assertEqual(res.context['user_cert_list'][3]['uploaded_date'], datetime.date(2018, 6, 10))
        self.assertEqual(res.context['user_cert_list'][3]['completion_date'], datetime.date(2017, 7, 13))
        self.assertEqual(res.context['user_cert_list'][3]['expiry_date'], datetime.date(2019, 7, 13))
        self.assertEqual(res.context['user_cert_list'][3]['name'], 'Transportation of Dangerous Goods Class 6.2 (Biological materials) Shipping Course for air')
        self.assertEqual(res.context['user_cert_list'][3]['expiry_in_years'], 2)

        self.assertEqual(res.context['user_cert_list'][4]['id'], 16)
        self.assertEqual(res.context['user_cert_list'][4]['user'], 11)
        self.assertEqual(res.context['user_cert_list'][4]['cert'], 16)
        self.assertIsNotNone(res.context['user_cert_list'][4]['cert_file'])
        self.assertEqual(res.context['user_cert_list'][4]['uploaded_date'], datetime.date(2020, 1, 10))
        self.assertEqual(res.context['user_cert_list'][4]['completion_date'], datetime.date(2014, 10, 1))
        self.assertEqual(res.context['user_cert_list'][4]['expiry_date'], datetime.date(2019, 10, 1))
        self.assertEqual(res.context['user_cert_list'][4]['name'], 'Biological Safety Course')
        self.assertEqual(res.context['user_cert_list'][4]['expiry_in_years'], 5)

        self.assertEqual(res.context['user_cert_list'][5]['id'], 22)
        self.assertEqual(res.context['user_cert_list'][5]['user'], 11)
        self.assertEqual(res.context['user_cert_list'][5]['cert'], 22)
        self.assertIsNotNone(res.context['user_cert_list'][5]['cert_file'])
        self.assertEqual(res.context['user_cert_list'][5]['uploaded_date'], datetime.date(2020, 1, 10))
        self.assertEqual(res.context['user_cert_list'][5]['completion_date'], datetime.date(2016, 10, 1))
        self.assertEqual(res.context['user_cert_list'][5]['expiry_date'], datetime.date(2019, 10, 1))
        self.assertEqual(res.context['user_cert_list'][5]['name'], 'Transportation of Dangerous Goods Class 7 (Radioactivity) Receiving Course for ground')
        self.assertEqual(res.context['user_cert_list'][5]['expiry_in_years'], 3)

        self.assertEqual(res.context['missing_cert_list'], [{'id': 2, 'name': 'Preventing and Addressing Workplace Bullying and Harassment Training', 'expiry_in_years': 0}, {'id': 5, 'name': 'Privacy and Information Security Fundamentals Training', 'expiry_in_years': 0}, {'id': 15, 'name': 'Chemical Safety Course', 'expiry_in_years': 5}])
        self.assertEqual(res.context['expired_cert_list'], [{'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_in_years': 5}, {'id': 23, 'name': 'Transportation of Dangerous Goods Class 6.2 (Biological materials) Shipping Course for air', 'expiry_in_years': 2}, {'id': 16, 'name': 'Biological Safety Course', 'expiry_in_years': 5}, {'id': 22, 'name': 'Transportation of Dangerous Goods Class 7 (Radioactivity) Receiving Course for ground', 'expiry_in_years': 3}])
        self.assertIsNotNone(res.context['form'])
        self.assertIsNotNone(res.context['viewing'], {})


    def test_upload_training_by_pi(self):
        print('\n- Test: upload a training - by pi')
        self.login(USERS[1], PASSWORD)

        user_id = 11
        training_id = 2

        user = self.api.get_user(user_id)
        self.assertFalse(user.usercert_set.filter(cert_id=training_id).exists())

        data = {
            'user': user_id,
            'cert': 2,
            'cert_file': SimpleUploadedFile(name='joss-woodhead-3wFRlwS91yk-unsplash.jpg', content=open(self.testing_image, 'rb').read(), content_type='image/jpeg'),
            'completion_date_year': 2020,
            'completion_date_month': 1,
            'completion_date_day': 15
        }

        res = self.client.post(reverse('user_trainings', args=[user_id]), data=data, format='multipart')
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! Preventing and Addressing Workplace Bullying and Harassment Training added.')
        self.assertEqual(res.url, reverse('user_trainings', args=[user.id]))
        self.assertRedirects(res, res.url)

        user2 = self.api.get_user(user_id)
        training = user2.usercert_set.filter(cert_id=training_id)
        self.assertTrue(training.exists())
        self.assertEqual(training.first().cert.name, 'Preventing and Addressing Workplace Bullying and Harassment Training')
        self.assertEqual(training.first().cert_file.name, 'users/11/certificates/2/joss-woodhead-3wFRlwS91yk-unsplash.jpg')
        training.delete()


    def test_view_user_trainings_by_myself(self):
        print("\n- Test: view user's trainings - by myself")
        self.login(USERS[2], PASSWORD)

        user_id = 11

        res = self.client.get(reverse('user_trainings', args=[user_id]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['app_user'].id, user_id)
        self.assertEqual(len(res.context['user_cert_list']), 6)

        self.assertEqual(res.context['user_cert_list'][0]['id'], 1)
        self.assertEqual(res.context['user_cert_list'][0]['user'], 11)
        self.assertEqual(res.context['user_cert_list'][0]['cert'], 1)
        self.assertIsNotNone(res.context['user_cert_list'][0]['cert_file'])
        self.assertEqual(res.context['user_cert_list'][0]['uploaded_date'], datetime.date(2018, 6, 10))
        self.assertEqual(res.context['user_cert_list'][0]['completion_date'], datetime.date(2014, 8, 15))
        self.assertEqual(res.context['user_cert_list'][0]['expiry_date'], datetime.date(2014, 8, 15))
        self.assertEqual(res.context['user_cert_list'][0]['name'], 'New Worker Safety Orientation')
        self.assertEqual(res.context['user_cert_list'][0]['expiry_in_years'], 0)

        self.assertEqual(res.context['user_cert_list'][1]['id'], 3)
        self.assertEqual(res.context['user_cert_list'][1]['user'], 11)
        self.assertEqual(res.context['user_cert_list'][1]['cert'], 3)
        self.assertIsNotNone(res.context['user_cert_list'][1]['cert_file'])
        self.assertEqual(res.context['user_cert_list'][1]['uploaded_date'], datetime.date(2018, 6, 10))
        self.assertEqual(res.context['user_cert_list'][1]['completion_date'], datetime.date(2014, 7, 10))
        self.assertEqual(res.context['user_cert_list'][1]['expiry_date'], datetime.date(2014, 7, 10))
        self.assertEqual(res.context['user_cert_list'][1]['name'], 'Workplace Violence Prevention Training')
        self.assertEqual(res.context['user_cert_list'][1]['expiry_in_years'], 0)

        self.assertEqual(res.context['user_cert_list'][2]['id'], 20)
        self.assertEqual(res.context['user_cert_list'][2]['user'], 11)
        self.assertEqual(res.context['user_cert_list'][2]['cert'], 20)
        self.assertIsNotNone(res.context['user_cert_list'][2]['cert_file'])
        self.assertEqual(res.context['user_cert_list'][2]['uploaded_date'], datetime.date(2018, 6, 10))
        self.assertEqual(res.context['user_cert_list'][2]['completion_date'], datetime.date(2014, 7, 14))
        self.assertEqual(res.context['user_cert_list'][2]['expiry_date'], datetime.date(2019, 7, 14))
        self.assertEqual(res.context['user_cert_list'][2]['name'], 'Biosafety for Permit Holders')
        self.assertEqual(res.context['user_cert_list'][2]['expiry_in_years'], 5)

        self.assertEqual(res.context['user_cert_list'][3]['id'], 23)
        self.assertEqual(res.context['user_cert_list'][3]['user'], 11)
        self.assertEqual(res.context['user_cert_list'][3]['cert'], 23)
        self.assertIsNotNone(res.context['user_cert_list'][3]['cert_file'])
        self.assertEqual(res.context['user_cert_list'][3]['uploaded_date'], datetime.date(2018, 6, 10))
        self.assertEqual(res.context['user_cert_list'][3]['completion_date'], datetime.date(2017, 7, 13))
        self.assertEqual(res.context['user_cert_list'][3]['expiry_date'], datetime.date(2019, 7, 13))
        self.assertEqual(res.context['user_cert_list'][3]['name'], 'Transportation of Dangerous Goods Class 6.2 (Biological materials) Shipping Course for air')
        self.assertEqual(res.context['user_cert_list'][3]['expiry_in_years'], 2)

        self.assertEqual(res.context['user_cert_list'][4]['id'], 16)
        self.assertEqual(res.context['user_cert_list'][4]['user'], 11)
        self.assertEqual(res.context['user_cert_list'][4]['cert'], 16)
        self.assertIsNotNone(res.context['user_cert_list'][4]['cert_file'])
        self.assertEqual(res.context['user_cert_list'][4]['uploaded_date'], datetime.date(2020, 1, 10))
        self.assertEqual(res.context['user_cert_list'][4]['completion_date'], datetime.date(2014, 10, 1))
        self.assertEqual(res.context['user_cert_list'][4]['expiry_date'], datetime.date(2019, 10, 1))
        self.assertEqual(res.context['user_cert_list'][4]['name'], 'Biological Safety Course')
        self.assertEqual(res.context['user_cert_list'][4]['expiry_in_years'], 5)

        self.assertEqual(res.context['user_cert_list'][5]['id'], 22)
        self.assertEqual(res.context['user_cert_list'][5]['user'], 11)
        self.assertEqual(res.context['user_cert_list'][5]['cert'], 22)
        self.assertIsNotNone(res.context['user_cert_list'][5]['cert_file'])
        self.assertEqual(res.context['user_cert_list'][5]['uploaded_date'], datetime.date(2020, 1, 10))
        self.assertEqual(res.context['user_cert_list'][5]['completion_date'], datetime.date(2016, 10, 1))
        self.assertEqual(res.context['user_cert_list'][5]['expiry_date'], datetime.date(2019, 10, 1))
        self.assertEqual(res.context['user_cert_list'][5]['name'], 'Transportation of Dangerous Goods Class 7 (Radioactivity) Receiving Course for ground')
        self.assertEqual(res.context['user_cert_list'][5]['expiry_in_years'], 3)

        self.assertEqual(res.context['missing_cert_list'], [{'id': 2, 'name': 'Preventing and Addressing Workplace Bullying and Harassment Training', 'expiry_in_years': 0}, {'id': 5, 'name': 'Privacy and Information Security Fundamentals Training', 'expiry_in_years': 0}, {'id': 15, 'name': 'Chemical Safety Course', 'expiry_in_years': 5}])
        self.assertEqual(res.context['expired_cert_list'], [{'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_in_years': 5}, {'id': 23, 'name': 'Transportation of Dangerous Goods Class 6.2 (Biological materials) Shipping Course for air', 'expiry_in_years': 2}, {'id': 16, 'name': 'Biological Safety Course', 'expiry_in_years': 5}, {'id': 22, 'name': 'Transportation of Dangerous Goods Class 7 (Radioactivity) Receiving Course for ground', 'expiry_in_years': 3}])
        self.assertIsNotNone(res.context['form'])
        self.assertIsNotNone(res.context['viewing'], {})


    def test_upload_training_by_myself(self):
        print('\n- Test: upload a training - by myself')
        self.login(USERS[2], PASSWORD)

        user_id = 11
        training_id = 2

        user = self.api.get_user(user_id)
        self.assertFalse(user.usercert_set.filter(cert_id=training_id).exists())

        data = {
            'user': user_id,
            'cert': training_id,
            'cert_file': SimpleUploadedFile(name='joss-woodhead-3wFRlwS91yk-unsplash.jpg', content=open(self.testing_image, 'rb').read(), content_type='image/jpeg'),
            'completion_date_year': 2020,
            'completion_date_month': 1,
            'completion_date_day': 15
        }

        res = self.client.post(reverse('user_trainings', args=[user_id]), data=data, format='multipart')
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! Preventing and Addressing Workplace Bullying and Harassment Training added.')
        self.assertEqual(res.url, reverse('user_trainings', args=[user_id]))
        self.assertRedirects(res, res.url)

        user2 = self.api.get_user(user_id)
        training = user2.usercert_set.filter(cert_id=training_id)
        self.assertTrue(training.exists())
        self.assertEqual(training.first().cert.name, 'Preventing and Addressing Workplace Bullying and Harassment Training')
        self.assertEqual(training.first().cert_file.name, 'users/11/certificates/2/joss-woodhead-3wFRlwS91yk-unsplash.jpg')
        training.delete()


    def test_upload_training_by_myself_duplicated(self):
        print('\n- Test: upload a training - by myself - duplicated')
        self.login(USERS[2], PASSWORD)

        user = self.api.get_user(11)
        user.usercert_set.all()

        data = {
            'user': user.id,
            'cert': 1,
            'cert_file': SimpleUploadedFile(name='joss-woodhead-3wFRlwS91yk-unsplash.jpg', content=open(self.testing_image, 'rb').read(), content_type='image/jpeg'),
            'completion_date_year': 2020,
            'completion_date_month': 1,
            'completion_date_day': 15
        }

        res = self.client.post(reverse('user_trainings', args=[user.id]), data=data, format='multipart')
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Error! Failed to add your training. The certificate already exists. If you wish to update a new training, please delete your old training first.')
        self.assertEqual(res.url, reverse('user_trainings', args=[user.id]))
        self.assertRedirects(res, res.url)


    def test_view_user_trainings_by_wrong_pi(self):
        print("\n- Test: view user's trainings - by wrong pi")
        self.login('testpi3', PASSWORD)

        res = self.client.get(reverse('user_trainings', args=[12]))
        self.assertEqual(res.status_code, 403)


    def test_upload_training_by_wrong_pi(self):
        print('\n- Test: upload a training - by wrong pi')
        self.login('testpi3', PASSWORD)

        user = self.api.get_user(12)

        data = {
            'user': user.id,
            'cert': 2,
            'cert_file': SimpleUploadedFile(name='joss-woodhead-3wFRlwS91yk-unsplash.jpg', content=open(self.testing_image, 'rb').read(), content_type='image/jpeg'),
            'completion_date_year': 2020,
            'completion_date_month': 1,
            'completion_date_day': 15
        }

        res = self.client.post(reverse('user_trainings', args=[user.id]), data=data, format='multipart')
        self.assertEqual(res.status_code, 403)


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


    def test_delete_user_training_by_admin(self):
        print('\n- Test: delete a training of users by admin')
        self.login()


        user_id = 11
        training_id = 15

        user = self.api.get_user(user_id)
        self.assertFalse(user.usercert_set.filter(cert_id=training_id).exists())

        data = {
            'user': user_id,
            'cert': training_id,
            'cert_file': SimpleUploadedFile(name='karsten-wurth-9qvZSH_NOQs-unsplash.jpg', content=open(self.testing_image2, 'rb').read(), content_type='image/jpeg'),
            'completion_date_year': 2020,
            'completion_date_month': 1,
            'completion_date_day': 15
        }

        res = self.client.post(reverse('user_trainings', args=[user_id]), data=data, format='multipart')
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! Chemical Safety Course added.')
        self.assertEqual(res.url, reverse('user_trainings', args=[user_id]))
        self.assertRedirects(res, res.url)

        user2 = self.api.get_user(user_id)
        training = user2.usercert_set.filter(cert_id=training_id)
        self.assertTrue(training.exists())
        self.assertEqual(training.first().cert.name, 'Chemical Safety Course')
        self.assertEqual(training.first().cert_file.name, 'users/11/certificates/15/karsten-wurth-9qvZSH_NOQs-unsplash.jpg')


        res = self.client.get(reverse('user_training_details', args=[user_id, training_id]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['app_user'].id, user_id)
        self.assertEqual(res.context['user_cert'].cert.id, training_id)

        user_id = res.context['app_user'].id
        training_id = res.context['user_cert'].cert.id

        data = {
            'user': user_id,
            'training': training_id
        }

        res = self.client.post(reverse('delete_user_training', args=[user_id]), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(res.status_code, 302)
        self.assertTrue(messages[0], 'Success! Chemical Safety Course deleted.')
        self.assertEqual(res.url, reverse('user_trainings', args=[user_id]))
        self.assertRedirects(res, res.url)


    def test_delete_user_cert_pi(self):
        print('\n- Test: delete a training of users by pi')
        self.login(USERS[1], PASSWORD)

        user_id = 11
        training_id = 17

        user = self.api.get_user(user_id)
        self.assertFalse(user.usercert_set.filter(cert_id=training_id).exists())

        data = {
            'user': user_id,
            'cert': training_id,
            'cert_file': SimpleUploadedFile(name='karsten-wurth-9qvZSH_NOQs-unsplash.jpg', content=open(self.testing_image2, 'rb').read(), content_type='image/jpeg'),
            'completion_date_year': 2020,
            'completion_date_month': 1,
            'completion_date_day': 15
        }

        res = self.client.post(reverse('user_trainings', args=[user_id]), data=data, format='multipart')
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! Radiation Safety Course added.')
        self.assertEqual(res.url, reverse('user_trainings', args=[user_id]))
        self.assertRedirects(res, res.url)

        user2 = self.api.get_user(user_id)
        training = user2.usercert_set.filter(cert_id=training_id)
        self.assertTrue(training.exists())
        self.assertEqual(training.first().cert.name, 'Radiation Safety Course')
        self.assertEqual(training.first().cert_file.name, 'users/11/certificates/17/karsten-wurth-9qvZSH_NOQs-unsplash.jpg')


        res = self.client.get(reverse('user_training_details', args=[user_id, training_id]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['app_user'].id, user_id)
        self.assertEqual(res.context['user_cert'].cert.id, training_id)

        user_id = res.context['app_user'].id
        training_id = res.context['user_cert'].cert.id

        data = {
            'user': user_id,
            'training': training_id
        }

        res = self.client.post(reverse('delete_user_training', args=[user_id]), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 403)

        training.delete()


    def test_delete_user_cert_by_user(self):
        print('\n- Test: delete a training of users by a user')
        self.login(USERS[2], PASSWORD)

        user_id = 11
        training_id = 15

        user = self.api.get_user(user_id)
        self.assertFalse(user.usercert_set.filter(cert_id=training_id).exists())

        data = {
            'user': user_id,
            'cert': training_id,
            'cert_file': SimpleUploadedFile(name='karsten-wurth-9qvZSH_NOQs-unsplash.jpg', content=open(self.testing_image2, 'rb').read(), content_type='image/jpeg'),
            'completion_date_year': 2020,
            'completion_date_month': 1,
            'completion_date_day': 15
        }

        res = self.client.post(reverse('user_trainings', args=[user_id]), data=data, format='multipart')
        self.assertEqual(res.status_code, 302)
        messages = self.messages(res)
        self.assertEqual(messages[0], 'Success! Chemical Safety Course added.')
        self.assertEqual(res.url, reverse('user_trainings', args=[user_id]))
        self.assertRedirects(res, res.url)

        user2 = self.api.get_user(user_id)
        training = user2.usercert_set.filter(cert_id=training_id)
        self.assertTrue(training.exists())
        self.assertEqual(training.first().cert.name, 'Chemical Safety Course')
        self.assertEqual(training.first().cert_file.name, 'users/11/certificates/15/karsten-wurth-9qvZSH_NOQs-unsplash.jpg')


        res = self.client.get(reverse('user_training_details', args=[user_id, training_id]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['app_user'].id, user_id)
        self.assertEqual(res.context['user_cert'].cert.id, training_id)

        user_id = res.context['app_user'].id
        training_id = res.context['user_cert'].cert.id

        data = {
            'user': user_id,
            'training': training_id
        }

        res = self.client.post(reverse('delete_user_training', args=[user_id]), data=urlencode(data), content_type=ContentType)
        messages = self.messages(res)
        self.assertEqual(res.status_code, 302)
        self.assertTrue(messages[0], 'Success! Chemical Safety Course deleted.')
        self.assertEqual(res.url, reverse('user_trainings', args=[user_id]))
        self.assertRedirects(res, res.url)
