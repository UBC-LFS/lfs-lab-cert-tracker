from django.test import TestCase
from lfs_lab_cert_tracker import api
from lfs_lab_cert_tracker.forms import CertForm
from lfs_lab_cert_tracker.models import Cert
from urllib.parse import urlencode

def setUpAdminLogin(self):
        user = api.create_user(first_name="Test", last_name="test", email="test@example.com", username="admin")
        user = api.switch_admin(user['id'])
        data = {"username": user['username'], "password": user['password']}
        self.client.post('/my_login/', data=data)

class UserModelTests(TestCase):

    def setUp(self):
        setUpAdminLogin(self)
    
    def testLoginAdmin(self):
        user = api.get_user_by_username("admin")
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'test')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.username, 'admin')

class CertModelTest(TestCase):

    def setUp(self):
        setUpAdminLogin(self)
        data = urlencode({'name': 'testing', 'expiry_in_years': 0, 'redirect_url': '/certificates/'})
        response = self.client.post('/api/certificates/',content_type="application/x-www-form-urlencoded",data=data)

    def testAddCert(self):
        cert = api.get_certs()[0]
        self.assertEqual(cert['name'], 'testing')
        self.assertEqual(cert['expiry_in_years'], 0)

    def testDeleteCert(self):
        cert = api.get_certs()[0]
        response = self.client.post('/api/certificates/' + str(cert['id']) + '/delete')
        self.assertEqual(response.status_code, 200)
        certs = api.get_certs()
        self.assertEqual(certs, [])

class LabsModelTest(TestCase):
    
    def setUp(self):
        setUpAdminLogin(self)
        lab = urlencode({'name': 'test', 'redirect_url': '/labs/'})
        self.client.post('/api/labs/',content_type="application/x-www-form-urlencoded", data=lab)

    def testAddLabs(self):
        lab = api.get_labs()[0]
        self.assertEqual(lab['name'], 'test')
    def testEditLabs(self):
        lab = api.get_labs()[0]
        newName = urlencode({'name': 'new test name','redirect_url': '/labs/'})
        response = self.client.post('/api/labs/' + str(lab['id']) + '/update', data=newName,content_type="application/x-www-form-urlencoded")
        print(api.get_labs())
