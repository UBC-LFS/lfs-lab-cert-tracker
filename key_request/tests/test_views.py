from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
# Replace this with your actual Group/Room model names
from key_request.models import ApprovalGroup

LOGIN_URL = reverse('accounts:local_login')

class RoomGroupCRUDAndFilterTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='test_admin',
            email='admin@test.com',
            password='password'
        )

        # 1. Create Mock Users
        self.user1 = User.objects.create_user(username='alice', first_name='Alice', last_name='Smith')
        self.user2 = User.objects.create_user(username='bob', first_name='Bob', last_name='Jones')
        self.user3 = User.objects.create_user(username='charlie', first_name='Charlie', last_name='Brown')

        # 2. Create Existing Test Groups
        self.group_alpha = ApprovalGroup.objects.create(name="Alpha Lab")
        self.group_alpha.members.set([self.user1.id, self.user2.id])

        self.group_beta = ApprovalGroup.objects.create(name="Beta Team")
        self.group_beta.members.set([self.user3.id])

        # 3. Login
        self.client.post(LOGIN_URL, data={'username': 'test_admin', 'password': 'password'})

    # ==========================================
    #  TESTING FILTERS (GET /all-groups/)
    # ==========================================
    def test_filter_by_group_name(self):
        response = self.client.get(reverse('key_request:all_groups'), {'name': 'Alpha'})
        self.assertIn(self.group_alpha, response.context['groups'])
        self.assertNotIn(self.group_beta, response.context['groups'])

    def test_filter_by_member_first_name(self):
        response = self.client.get(reverse('key_request:all_groups'), {'member_first_name': 'Bob'})
        self.assertIn(self.group_alpha, response.context['groups'])
        self.assertNotIn(self.group_beta, response.context['groups'])

    def test_filter_by_member_last_name(self):
        response = self.client.get(reverse('key_request:all_groups'), {'member_last_name': 'Brown'})
        self.assertIn(self.group_beta, response.context['groups'])
        self.assertNotIn(self.group_alpha, response.context['groups'])

    def test_filter_by_member_ids_list(self):
        response = self.client.get(reverse('key_request:all_groups') + f"?members[]={self.user1.id}&members[]={self.user2.id}")
        self.assertIn(self.group_alpha, response.context['groups'])

    def test_filter_by_member_ids_list_no_results_for_partial_group_match(self):
        response = self.client.get(reverse('key_request:all_groups') + f"?members[]={self.user1.id}")
        self.assertNotIn(self.group_alpha, response.context['groups'])

    # ==========================================
    #  TESTING CREATION (POST /create-group)
    # ==========================================
    def test_create_group_success(self):
        payload = {
            'name': 'Gamma Lab',
            'member_ids': f"{self.user1.id},{self.user3.id}"
        }
        response = self.client.post(reverse('key_request:create_group'), data=payload)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ApprovalGroup.objects.filter(name='Gamma Lab').exists())

    def test_create_fails_without_name(self):
        payload = {
            'name': '',
            'member_ids': f"{self.user1.id}"
        }
        response = self.client.post(reverse('key_request:create_group'), data=payload, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Form is invalid")


    def test_create_fails_with_zero_members(self):
        payload = {
            'name': 'Orphan Group',
            'member_ids': ''
        }
        response = self.client.post(reverse('key_request:create_group'), data=payload, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Form is invalid")

    # ==========================================
    #  TESTING EDITING (POST /edit-group/)
    # ==========================================
    def test_edit_group_fails_with_no_name_or_members(self):
        url = reverse('key_request:edit_group', kwargs={'group_id': self.group_alpha.id})

        response = self.client.post(url, data={'name': '', 'member_ids': f"{self.user1.id}"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Form is invalid")

        response = self.client.post(url, data={'name': 'Alpha New Name', 'member_ids': ''}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Form is invalid")

    # ==========================================
    #  TESTING DELETION (POST /all-groups/delete/)
    # ==========================================
    def test_delete_group_success(self):
        response = self.client.post(reverse('key_request:delete_group'), data={'group': self.group_alpha.id})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ApprovalGroup.objects.filter(id=self.group_alpha.id).exists())