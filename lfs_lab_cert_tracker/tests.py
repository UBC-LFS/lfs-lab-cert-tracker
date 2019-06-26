from django.test import TestCase
from lfs_lab_cert_tracker import api

class UserModelTests(TestCase):

    def setUp(self):
        api.create_user(first_name="Test", last_name="test", email="test@example.com", username="admin")
    
    def testLoginAdmin(self):
        user = api.get_user_by_username("admin")
        data={"username": user.username, "password": user.password}

        response = self.client.post('/my_login/', data=data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')

        response2 = self.client.get(response.url)
        self.assertEqual(response2.status_code, 302)
        self.assertContains(response2.url, '/users/')

        response3 = self.client.get(response2.url + '/')
        print(response3)

    def testAddCert(self):
        response = self.client.get('/users/1/certificates')
        print(response)