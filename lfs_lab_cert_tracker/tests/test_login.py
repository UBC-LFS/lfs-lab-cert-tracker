from django.test import TestCase
from django.contrib.auth.models import User as AuthUser
from lfs_lab_cert_tracker.utils import Api
from .test_users import DATA, USERS


class LoginTest(TestCase):
    fixtures = DATA

    @classmethod
    def setUpTestData(cls):
        print('\nLogin testing has started ==>')
        cls.api = Api()

    def saml_authenticate(self, saml_auth):
        ''' test saml authenticate function '''
        if not saml_auth:
            return None

        if saml_auth['auth']:
            user_data = saml_auth['attrs']

            found_user = AuthUser.objects.filter(username=user_data['username'])
            if found_user.exists():
                return found_user.first()
            else:
                user = AuthUser(username=user_data['username'], first_name=user_data['first_name'], last_name=user_data['last_name'], email=user_data['email'])
                user.set_unusable_password()
                user.save()

                return user

        return None


    def test_login_success_new_user(self):
        print('- Test: login success with a new user')
        saml_data = {
            'auth': True,
            'attrs': {
                'username': 'new.user123',
                'first_name': 'New',
                'last_name': 'User123',
                'email': 'new.user123@example.com'
            }
        }

        user = self.saml_authenticate(saml_data)
        self.assertIsNotNone(user)
        self.assertEqual(user.username, saml_data['attrs']['username'])
        self.assertEqual(user.email, saml_data['attrs']['email'])
        self.assertEqual(user.first_name, saml_data['attrs']['first_name'])
        self.assertEqual(user.last_name, saml_data['attrs']['last_name'])


    def test_login_success_created_user(self):
        print('- Test: login success with a created user')

        user = self.api.get_user(USERS[2], 'username')
        self.assertIsNotNone(user)

        saml_data = {
            'auth': True,
            'attrs': {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'username': user.username
            }
        }

        auth_user = self.saml_authenticate(saml_data)
        self.assertIsNotNone(auth_user)
        self.assertEqual(auth_user.username, saml_data['attrs']['username'])
        self.assertEqual(auth_user.email, saml_data['attrs']['email'])
        self.assertEqual(auth_user.first_name, saml_data['attrs']['first_name'])
        self.assertEqual(auth_user.last_name, saml_data['attrs']['last_name'])
