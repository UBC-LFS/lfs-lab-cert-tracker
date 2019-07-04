from django.test import TestCase
from lfs_lab_cert_tracker import api
from lfs_lab_cert_tracker.forms import CertForm
from lfs_lab_cert_tracker.models import Cert
from urllib.parse import urlencode
from django.contrib.auth.models import User as AuthUser
from django.contrib.auth.hashers import make_password
from django.forms.models import model_to_dict

def create_user(first_name, last_name, email, username):
    user = api.get_user_by_username(username)
    if user:
        return None
    # TODO: Replace the need to create an AuthUser with a password
    user_created = AuthUser.objects.create(
        first_name=first_name,
        last_name=last_name,
        username=username,
        email=email,
        password=make_password(''),
    )
    return model_to_dict(user_created)

def setUpAdminLogin(self):
    user = create_user(first_name="Test", last_name="test", email="test@example.com", username="admin")
    user = api.switch_admin(user['id'])
    data = {"username": user['username'], "password": user['password']}
    self.client.post('/my_login/', data=data)

def setUpUser(self):
    newUser = urlencode({
        'first_name': 'Bob',
        'last_name': 'Jones',
        'email': 'bobjones@example.com',
        'username': 'bobjones2019',
        'redirect_url': '/users/',
    })
    self.client.post('/api/users/', data=newUser, content_type="application/x-www-form-urlencoded")
    return api.get_user_by_username('bobjones2019')

def setUpCert(self):
    data = urlencode({'name': 'testing', 'expiry_in_years': 0, 'redirect_url': '/certificates/'})
    self.client.post('/api/certificates/', content_type="application/x-www-form-urlencoded", data=data)

def setUpLab(self):
    lab = urlencode({'name': 'test', 'redirect_url': '/labs/'})
    self.client.post('/api/labs/',content_type="application/x-www-form-urlencoded", data=lab)

class UserModelTests(TestCase):

    def setUp(self):
        setUpAdminLogin(self)
        setUpUser(self)
    
    def testLoginAdmin(self):
        user = api.get_user_by_username("admin")
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'test')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.username, 'admin')

    def testAddUser(self):
        user = api.get_user_by_username('bobjones2019')
        self.assertEqual(user.first_name, 'Bob')
        self.assertEqual(user.last_name, 'Jones')
        self.assertEqual(user.email, 'bobjones@example.com')
        self.assertEqual(user.username, 'bobjones2019')

    # def testRegUserPermission(self):
    #     user = api.get_user_by_username('bobjones2019')
    #     data = {"username": user.username, "password": user.password}
    #     self.client.post('/my_login/', data=data)
    #     response = self.client.get('/users/')
    #     self.assertEqual(response.status_code, 403)
    #     data = urlencode({'name': 'testing', 'expiry_in_years': 0, 'redirect_url': '/certificates/'})
    #     response = self.client.post('/api/certificates/', content_type="application/x-www-form-urlencoded", data=data)
    #     self.assertEqual(response.status_code, 403)
    #     lab = urlencode({'name': 'test', 'redirect_url': '/labs/'})
    #     response = self.client.post('/api/labs/',content_type="application/x-www-form-urlencoded", data=lab)
    #     self.assertEqual(response.status_code, 403)

class CertModelTest(TestCase):

    def setUp(self):
        setUpAdminLogin(self)
        setUpCert(self)

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

    def testAddCertToUser(self):
        cert = api.get_certs()[0]
        user = api.get_user_by_username('admin')
        api.update_or_create_user_cert(user_id=user.id,cert_id=cert['id'],cert_file='testCert.pdf', completion_date="2019-07-03",expiry_date="2019-07-03")
        userCert = api.get_user_certs(user.id)
        self.assertEqual(userCert[0]['cert'], cert['id'])

    def testAddCertToLab(self):
        setUpLab(self)
        cert = api.get_certs()[0]
        lab = api.get_labs()[0]
        data = urlencode({'cert': cert['id'], 'redirect_url': ['']})
        response = self.client.post('/api/labs/' + str(lab['id']) + '/certificates/', data=data, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 302)
        labCerts = api.get_lab_certs(lab['id'])
        self.assertEqual(labCerts[0]['name'], 'testing')
    
    def testExpiredCert(self):
        data = urlencode({'name': 'testexpire', 'expiry_in_years': 1, 'redirect_url': '/certificates/'})
        self.client.post('/api/certificates/', content_type="application/x-www-form-urlencoded", data=data)
        cert = list(filter(lambda x: x['name'] == 'testexpire', api.get_certs()))[0]
        user = api.get_user_by_username('admin')
        api.update_or_create_user_cert(user_id=user.id,cert_id=cert['id'],cert_file='testCert.pdf', completion_date="2017-07-03",expiry_date="2018-07-03")
        expiredCerts = api.get_expired_certs(user.id)
        self.assertEqual(expiredCerts[0]['name'], 'testexpire')

class LabsModelTest(TestCase):
    
    def setUp(self):
        setUpAdminLogin(self)
        setUpLab(self)

    def testAddLabs(self):
        lab = api.get_labs()[0]
        self.assertEqual(lab['name'], 'test')

    def testEditLabs(self):
        lab = api.get_labs()[0]
        newName = urlencode({'name': 'new test name','redirect_url': '/labs/'})
        response = self.client.post('/api/labs/' + str(lab['id']) + '/update', data=newName, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 302)
        lab = api.get_labs()[0]
        self.assertEqual(lab['name'], 'new test name')
    
    def testDeleteLabs(self):
        lab = api.get_labs()[0]
        deleteForm = urlencode({'redirect_url': '/labs/'})
        response = self.client.post('/api/labs/' + str(lab['id']) + '/delete', data=deleteForm, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 302)
        labs = api.get_labs()
        self.assertEqual(len(labs), 0)

    def testAddUserToLab(self):
        user = setUpUser(self)
        lab = api.get_labs()[0]
        data = urlencode({'user': user.username, 'role': 0, 'redirect_url': ['/labs/5', '/labs/5']})
        response = self.client.post('/api/labs/' + str(lab['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 302)
        userLabs = api.get_user_labs(user.id)
        self.assertEqual(userLabs[0]['name'], 'test')
    
    def testAddPIToLab(self):
        user = setUpUser(self)
        lab = api.get_labs()[0]
        data = urlencode({'user': user.username, 'role': 1, 'redirect_url': ['/labs/5', '/labs/5']})
        response = self.client.post('/api/labs/' + str(lab['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 302)
        userLabs = api.get_user_labs(user.id,is_principal_investigator=True)
        self.assertEqual(userLabs[0]['name'], 'test')

    def testRemoveUserFromLab(self):
        user = setUpUser(self)
        lab = api.get_labs()[0]
        data = urlencode({'user': user.username, 'role': 0, 'redirect_url': ['/labs/5', '/labs/5']})
        self.client.post('/api/labs/' + str(lab['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        data = urlencode({'redirect_url': ''})
        response = self.client.post('/api/users/' + str(user.id) + '/labs/' + str(lab['id']) + '/delete', data=data, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 302)
        userLabs = api.get_user_labs(user.id)
        self.assertEqual(len(userLabs), 0)

class UserLabCertModelTest(TestCase):
    
    def setUp(self):
        setUpAdminLogin(self)
        setUpUser(self)
        setUpCert(self)
        setUpLab(self)

    def testUserMissingCerts(self):
        user = api.get_user_by_username('bobjones2019')
        cert = api.get_certs()[0]
        lab = api.get_labs()[0]
        data = urlencode({'cert': cert['id'], 'redirect_url': ['']})
        self.client.post('/api/labs/' + str(lab['id']) + '/certificates/', data=data, content_type="application/x-www-form-urlencoded")
        data = urlencode({'redirect_url': ''})
        response = self.client.post('/api/users/' + str(user.id) + '/labs/' + str(lab['id']) + '/delete', data=data, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 302)
        missingCerts = api.get_missing_lab_certs(user.id, lab['id'])
        self.assertEqual(missingCerts[0]['name'], 'testing')

    def testUserNoMissingCerts(self):
        user = api.get_user_by_username('bobjones2019')
        cert = api.get_certs()[0]
        lab = api.get_labs()[0]
        data = urlencode({'cert': cert['id'], 'redirect_url': ['']})
        self.client.post('/api/labs/' + str(lab['id']) + '/certificates/', data=data, content_type="application/x-www-form-urlencoded")
        data = urlencode({'redirect_url': ''})
        self.client.post('/api/users/' + str(user.id) + '/labs/' + str(lab['id']) + '/delete', data=data, content_type="application/x-www-form-urlencoded")
        api.update_or_create_user_cert(user_id=user.id,cert_id=cert['id'],cert_file='testCert.pdf', completion_date="2019-07-03",expiry_date="2019-07-03")
        missingCerts = api.get_missing_lab_certs(user.id, lab['id'])
        self.assertEqual(len(missingCerts), 0)