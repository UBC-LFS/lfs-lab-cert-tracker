import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from key_request.models import ApprovalGroup

LOGIN_URL = reverse('accounts:local_login')

class AsyncValidationAndAutofillTests(TestCase):

    def setUp(self):

        self.admin_user = User.objects.create_superuser(
            username='test_admin',
            email='admin@test.com',
            password='password'
        )

        self.client = Client()

        self.user_alice = User.objects.create_user(username='alice', first_name='Alice', last_name='Smith')

        self.user_bob = User.objects.create_user(username='bob', first_name='Bob', last_name='Jones')
        self.client.post(LOGIN_URL, data={'username': 'test_admin', 'password': 'password'})


        # Existing duplicate check group
        self.duplicate_target = ApprovalGroup.objects.create(name="Alice_Smith's Room Group")
        self.duplicate_target.members.set([self.user_alice.id, self.user_bob.id])

    # ==========================================
    #  TESTING AUTOFILL / SUGGESTIONS
    # ==========================================
    def test_user_autofill_returns_correct_payload(self):

        url = reverse('key_request:user_autofill') + "?name_q=Ali"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)


        data = json.loads(response.content)

        self.assertIn('data', data)
        self.assertEqual(data['data'][0]['first_name'], 'Alice')

    # ==========================================
    #  TESTING DUPLICATE MEMBERS WARNING CHECK
    # ==========================================
    def test_check_duplicate_endpoint_triggers_on_matching_composition(self):
        url = reverse('key_request:validate_room_group')

        payload = {
            'members[]': [self.user_alice.id, self.user_bob.id],
            'name': "Bob_Jones' Room Group"
        }

        response = self.client.get(url, data=payload)
        self.assertEqual(response.status_code, 200)

        response_json = json.loads(response.content)
        self.assertTrue(response_json.get('has_duplicate'))
        self.assertEqual(response_json.get('match_type'), 'composition')
        api_data = response_json['data']


        self.assertEqual(api_data.get('num_matches'), 1)
        self.assertIn("Alice_Smith's Room Group", api_data.get('group_names', []))

    def test_check_duplicate_endpoint_triggers_on_matching_name(self):
        url = reverse('key_request:validate_room_group')

        payload = {
            'members[]': [self.user_alice.id],
            'name': "Alice_Smith's Room Group"
        }

        response = self.client.get(url, data=payload)
        self.assertEqual(response.status_code, 200)

        response_json = json.loads(response.content)
        self.assertTrue(response_json.get('has_duplicate'))
        self.assertEqual(response_json.get('match_type'), 'name')
        api_data = response_json['data']


        self.assertEqual(set(api_data.get('group_members')), {"Alice Smith", "Bob Jones"})

    def test_check_duplicate_endpoint_not_triggers_on_matching_name_for_edit(self):
        url = reverse('key_request:validate_room_group')

        payload = {
            'members[]': [self.user_alice.id],
            'name': "Alice_Smith's Room Group",
            'group_id': self.duplicate_target.id
        }

        response = self.client.get(url, data=payload)
        self.assertEqual(response.status_code, 200)

        response_json = json.loads(response.content)
        self.assertFalse(response_json.get('has_duplicate'))

    def test_check_duplicate_endpoint_clear_on_unique_name(self):
        url = reverse('key_request:validate_room_group')

        payload = {
            'members[]': [self.user_alice.id],
            'name': "Lab 112's Room Group"
        }
        response = self.client.get(url, data=payload)

        response_json = json.loads(response.content)
        self.assertTrue('has_duplicate' in response_json.keys())
        self.assertFalse(response_json.get('has_duplicate'))

    def test_check_duplicate_endpoint_clear_on_unique_composition(self):
        url = reverse('key_request:validate_room_group')

        payload = {'members[]': [self.user_alice.id]}
        response = self.client.get(url, data=payload)

        response_json = json.loads(response.content)
        self.assertTrue('has_duplicate' in response_json.keys())
        self.assertFalse(response_json.get('has_duplicate'))