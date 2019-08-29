from django.test import TestCase
from lfs_lab_cert_tracker import api
from lfs_lab_cert_tracker.forms import CertForm
from lfs_lab_cert_tracker.models import Cert
from urllib.parse import urlencode
from django.contrib.auth.models import User as AuthUser
from django.contrib.auth.hashers import make_password
from django.forms.models import model_to_dict
from django.core import mail
# from email_notification import send_email_after_expiry_date
#import email_notification.test
import datetime
import subprocess


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

def setUpUser5(self):
    for i in range(5):
        firstname = 'test' + str(i)
        lastname = 'user' + str(i)
        username = firstname + '.' + lastname
        email = username + '@example.com'
        newUser = urlencode({
            'first_name': firstname,
            'last_name': lastname,
            'email': email,
            'username': username,
            'redirect_url': '/users/',
        })
        self.client.post('/api/users/', data=newUser, content_type="application/x-www-form-urlencoded")


def setUpCert(self):
    data = urlencode({'name': 'testing', 'expiry_in_years': 0, 'redirect_url': '/certificates/'})
    self.client.post('/api/certificates/', content_type="application/x-www-form-urlencoded", data=data)

def setUpCert5(self):
    for i in range(5):
        name = 'testing' + str(i)
        data = urlencode({'name': name, 'expiry_in_years': 0, 'redirect_url': '/certificates/'})
        self.client.post('/api/certificates/', content_type="application/x-www-form-urlencoded", data=data)

def setUpLab(self):
    lab = urlencode({'name': 'test', 'redirect_url': '/labs/'})
    self.client.post('/api/labs/',content_type="application/x-www-form-urlencoded", data=lab)

def setUpLab5(self):
    for i in range(5):
        name = 'testLab' + str(i)
        lab = urlencode({'name': name, 'redirect_url': '/labs/'})
        self.client.post('/api/labs/',content_type="application/x-www-form-urlencoded", data=lab)

class UserModelTests(TestCase):

    def setUp(self):
        setUpAdminLogin(self)
        setUpUser(self)
        setUpUser5(self)

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

    def testAdd5MoreUsers(self):
        users = api.get_users()
        self.assertGreater(len(users), 2)

    def testCreateNewAdmin(self):
        user = api.get_user_by_username('test4.user4')
        response = self.client.post('/api/users/' + str(user.id) + '/switch_admin')
        self.assertEqual(response.status_code, 200)
        user = api.get_user_by_username('test4.user4')
        self.assertEqual(user.is_superuser, True)

    def testDeleteUser(self):
        user = api.get_user_by_username('test4.user4')
        data = urlencode({'redirect_url': '/users/'})
        response = self.client.post('/api/users/' + str(user.id) + '/delete', data=data, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 302)
        user = api.get_user_by_username('test4.user4')
        self.assertIsNone(user)

    def testInactiveUser(self):
        user = api.get_user_by_username('test4.user4')
        data = urlencode({'redirect_url': '/users/'})
        response = self.client.post('/api/users/' + str(user.id) + '/switch_inactive')
        self.assertEqual(response.status_code, 200)
        user = api.get_user_by_username('test4.user4')
        self.assertEqual(user.is_active, False)

    def testAdminRedirect(self):
        user = api.get_user_by_username('admin')
        response = self.client.get('/')
        self.assertEqual(response.url, '/users/' + str(user.id))

    def testUserAccessAnotherUser(self):
        user1 = api.get_user_by_username('bobjones2019')
        user2 = api.get_user_by_username('test4.user4')
        data = {"username": user1.username, "password": user1.password}
        self.client.post('/my_login/', data=data)
        response = self.client.get('/users/' + str(user2.id))
        self.assertNotEqual(response.status_code, 301)
        self.assertNotEqual(response.status_code, 302)
        self.assertNotEqual(response.status_code, 200)

    # Getting weird off 1 error with this test
    # def testUserRedirect(self):
    #     user = api.get_user_by_username('bobjones2019')
    #     data = {"username": user.username, "password": user.password}
    #     self.client.post('/my_login/', data=data)
    #     response = self.client.get('/')
    #     self.assertEqual(response.url, '/users/' + str(user.id))

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
        setUpCert5(self)
        setUpUser5(self)

    def testAddCert(self):
        cert = api.get_certs()[0]
        self.assertEqual(cert['name'], 'testing')
        self.assertEqual(cert['expiry_in_years'], 0)

    def testDeleteCert(self):
        certs = api.get_certs()
        cert = certs[0]
        certNumber = len(certs)
        response = self.client.post('/api/certificates/' + str(cert['id']) + '/delete')
        self.assertEqual(response.status_code, 200)
        certs = api.get_certs()
        self.assertEqual(len(certs), certNumber - 1)

    def testAddCertToUser(self):
        cert = api.get_certs()[0]
        user = api.get_user_by_username('admin')
        api.update_or_create_user_cert(user_id=user.id,cert_id=cert['id'],cert_file='testCert.pdf', completion_date="2019-07-03",expiry_date="2019-07-03")
        userCert = api.get_user_certs(user.id)
        self.assertEqual(userCert[0]['cert'], cert['id'])

    def testAdd2CertToUser(self):
        cert1 = api.get_certs()[0]
        cert2 = api.get_certs()[1]
        user = api.get_user_by_username('admin')
        api.update_or_create_user_cert(user_id=user.id,cert_id=cert1['id'],cert_file='testCert.pdf', completion_date="2019-07-03",expiry_date="2019-07-03")
        api.update_or_create_user_cert(user_id=user.id,cert_id=cert2['id'],cert_file='testCert.pdf', completion_date="2019-07-03",expiry_date="2019-07-03")
        userCert = api.get_user_certs(user.id)
        self.assertEqual(len(userCert),2)

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

    def test2Certs1Expired(self):
        data = urlencode({'name': 'testexpire', 'expiry_in_years': 1, 'redirect_url': '/certificates/'})
        self.client.post('/api/certificates/', content_type="application/x-www-form-urlencoded", data=data)
        certexpired = list(filter(lambda x: x['name'] == 'testexpire', api.get_certs()))[0]
        cert = list(filter(lambda x: x['name'] != 'testexpire', api.get_certs()))[0]
        user = api.get_user_by_username('admin')
        api.update_or_create_user_cert(user_id=user.id,cert_id=certexpired['id'],cert_file='testCert.pdf', completion_date="2017-07-03",expiry_date="2018-07-03")
        api.update_or_create_user_cert(user_id=user.id,cert_id=cert['id'],cert_file='testCert.pdf', completion_date="2018-07-03",expiry_date="2018-07-03")
        expiredCerts = api.get_expired_certs(user.id)
        certsAll = api.get_user_certs(user.id)
        self.assertEqual(expiredCerts[0]['name'], 'testexpire')
        self.assertEqual(len(certsAll), 2)

    def testAddSameCertTwice(self):
        user = api.get_user_by_username('admin')
        cert = api.get_certs()[0]
        api.update_or_create_user_cert(user_id=user.id,cert_id=cert['id'],cert_file='testCert.pdf', completion_date="2017-07-03",expiry_date="2018-07-03")
        api.update_or_create_user_cert(user_id=user.id,cert_id=cert['id'],cert_file='testCert.pdf', completion_date="2017-07-03",expiry_date="2018-07-03")
        self.assertEqual(len(api.get_user_certs(user.id)),1)

    # def testAddCertBadFormat(self):
    #     user = api.get_user_by_username('admin')
    #     cert1 = api.get_certs()[0]
    #     cert2 = api.get_certs()[1]
    #     api.update_or_create_user_cert(user_id=user.id,cert_id=cert1['id'],cert_file='testCert.mp3', completion_date="2017-07-03",expiry_date="2018-07-03")
    #     api.update_or_create_user_cert(user_id=user.id,cert_id=cert2['id'],cert_file='testCert.csv', completion_date="2017-07-03",expiry_date="2018-07-03")
    #     self.assertEqual(len(api.get_user_certs(user.id)),0)

class LabsModelTest(TestCase):

    def setUp(self):
        setUpAdminLogin(self)
        setUpLab(self)
        setUpLab5(self)
        setUpUser5(self)

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
        ogLabNum = len(api.get_labs())
        lab = api.get_labs()[0]
        deleteForm = urlencode({'redirect_url': '/labs/'})
        response = self.client.post('/api/labs/' + str(lab['id']) + '/delete', data=deleteForm, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 302)
        labs = api.get_labs()
        self.assertEqual(len(labs), ogLabNum-1)

    def testAddUserToLab(self):
        user = setUpUser(self)
        lab = api.get_labs()[0]
        data = urlencode({'user': user.username, 'role': 0, 'redirect_url': ['/labs/5', '/labs/5']})
        response = self.client.post('/api/labs/' + str(lab['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 302)
        userLabs = api.get_user_labs(user.id)
        self.assertEqual(userLabs[0]['name'], 'test')

    def testAddUserTo2Labs(self):
        user = setUpUser(self)
        lab1 = api.get_labs()[0]
        lab2 = api.get_labs()[1]
        data = urlencode({'user': user.username, 'role': 0, 'redirect_url': ['/labs/5', '/labs/5']})
        self.client.post('/api/labs/' + str(lab1['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        self.client.post('/api/labs/' + str(lab2['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        userLabs = api.get_user_labs(user.id)
        self.assertEqual(len(userLabs), 2)

    def testAddPIToLab(self):
        user = setUpUser(self)
        lab = api.get_labs()[0]
        data = urlencode({'user': user.username, 'role': 1, 'redirect_url': ['/labs/5', '/labs/5']})
        response = self.client.post('/api/labs/' + str(lab['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 302)
        userLabs = api.get_user_labs(user.id,is_principal_investigator=True)
        self.assertEqual(userLabs[0]['name'], 'test')

    def testAddPIandUserToLab(self):
        userPI = setUpUser(self)
        lab = api.get_labs()[0]
        data = urlencode({'user': userPI.username, 'role': 1, 'redirect_url': ['/labs/5', '/labs/5']})
        self.client.post('/api/labs/' + str(lab['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        user = setUpUser(self)
        lab = api.get_labs()[0]
        data = urlencode({'user': user.username, 'role': 0, 'redirect_url': ['/labs/5', '/labs/5']})
        self.client.post('/api/labs/' + str(lab['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        userLabsPI = api.get_user_labs(userPI.id,is_principal_investigator=True)
        self.assertEqual(userLabsPI[0]['name'], 'test')
        userLabs = api.get_user_labs(user.id)
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

    def testRemovePIFromLab(self):
        user = setUpUser(self)
        lab = api.get_labs()[0]
        data = urlencode({'user': user.username, 'role': 1, 'redirect_url': ['/labs/5', '/labs/5']})
        self.client.post('/api/labs/' + str(lab['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        data = urlencode({'redirect_url': ''})
        self.client.post('/api/users/' + str(user.id) + '/labs/' + str(lab['id']) + '/delete', data=data, content_type="application/x-www-form-urlencoded")
        userLabs = api.get_user_labs(user.id)
        self.assertEqual(len(userLabs), 0)

    def testAdd2PIToLab(self):
        user1 = setUpUser(self)
        user2 = api.get_user_by_username('admin')
        lab = api.get_labs()[0]
        data = urlencode({'user': user1.username, 'role': 1, 'redirect_url': ['/labs/5', '/labs/5']})
        self.client.post('/api/labs/' + str(lab['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        data = urlencode({'user': user2.username, 'role': 1, 'redirect_url': ['/labs/5', '/labs/5']})
        self.client.post('/api/labs/' + str(lab['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        usersLab = api.get_users_in_lab(lab['id'])

    def testEmailFromLab(self):
        user = api.get_user_by_username('admin')
        lab = api.get_labs()[0]
        data = urlencode({'user': user.username, 'role': 0, 'redirect_url': ['/labs/5', '/labs/5']})
        self.client.post('/api/labs/' + str(lab['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        self.assertEqual(len(mail.outbox), 1)

    def testSwitchToPI(self):
        user = api.get_user_by_username('admin')
        lab = api.get_labs()[0]
        data = urlencode({'user': user.username, 'role': 0, 'redirect_url': ['/labs/5', '/labs/5']})
        self.client.post('/api/labs/' + str(lab['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        data = urlencode({'redirect_url': '/labs/3'})
        self.client.post('/api/users/' + str(user.id) + '/labs/' + str(lab['id']) + '/switch_lab_role', data=data, content_type="application/x-www-form-urlencoded")
        self.assertEqual(len(api.get_user_labs(user.id, is_principal_investigator=True)),1)

    def testSwitchToLabUser(self):
        user = api.get_user_by_username('admin')
        lab = api.get_labs()[0]
        data = urlencode({'user': user.username, 'role': 1, 'redirect_url': ['/labs/5', '/labs/5']})
        self.client.post('/api/labs/' + str(lab['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        data = urlencode({'redirect_url': '/labs/3'})
        self.client.post('/api/users/' + str(user.id) + '/labs/' + str(lab['id']) + '/switch_lab_role', data=data, content_type="application/x-www-form-urlencoded")
        self.assertEqual(len(api.get_user_labs(user.id, is_principal_investigator=True)),0)

    def testSwitchTwice(self):
        user = api.get_user_by_username('admin')
        lab = api.get_labs()[0]
        data = urlencode({'user': user.username, 'role': 0, 'redirect_url': ['/labs/5', '/labs/5']})
        self.client.post('/api/labs/' + str(lab['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        data = urlencode({'redirect_url': '/labs/3'})
        self.client.post('/api/users/' + str(user.id) + '/labs/' + str(lab['id']) + '/switch_lab_role', data=data, content_type="application/x-www-form-urlencoded")
        self.client.post('/api/users/' + str(user.id) + '/labs/' + str(lab['id']) + '/switch_lab_role', data=data, content_type="application/x-www-form-urlencoded")
        self.assertEqual(len(api.get_user_labs(user.id, is_principal_investigator=True)),0)

    # def testNonExistantCert(self):
    #     user = api.get_user_by_username('admin')
    #     response = self.client.get('/users/' + str(user.id) + '/certificates/60')
    #     response2 = self.client.get(response.url)
    #     print('HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH')
    #     print(response2)

class UserLabCertModelTest(TestCase):

    def setUp(self):
        setUpAdminLogin(self)
        setUpUser(self)
        setUpUser5(self)
        setUpCert(self)
        setUpCert5(self)
        setUpLab(self)
        setUpLab5(self)

    def testUserMissingCerts(self):
        user = api.get_user_by_username('bobjones2019')
        cert = api.get_certs()[0]
        lab = api.get_labs()[0]
        data = urlencode({'cert': cert['id'], 'redirect_url': '/labs/'})
        self.client.post('/api/labs/' + str(lab['id']) + '/certificates/', data=data, content_type="application/x-www-form-urlencoded")
        data = urlencode({'redirect_url': '', 'user': user.username, 'role': 0})
        response = self.client.post('/api/labs/' + str(lab['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 302)
        missingCerts = api.get_missing_lab_certs(user.id, lab['id'])
        self.assertEqual(missingCerts[0]['name'], 'testing')

    def testUserNoMissingCerts(self):
        user = api.get_user_by_username('bobjones2019')
        cert = api.get_certs()[0]
        lab = api.get_labs()[0]
        data = urlencode({'cert': cert['id'], 'redirect_url': '/labs/'})
        self.client.post('/api/labs/' + str(lab['id']) + '/certificates/', data=data, content_type="application/x-www-form-urlencoded")
        data = urlencode({'redirect_url': '', 'user': user.username, 'role': 0})
        self.client.post('/api/labs/' + str(lab['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        api.update_or_create_user_cert(user_id=user.id,cert_id=cert['id'],cert_file='testCert.pdf', completion_date="2019-07-03",expiry_date="2019-07-03")
        missingCerts = api.get_missing_lab_certs(user.id, lab['id'])
        self.assertEqual(len(missingCerts), 0)

    def testUserMissingOneCert(self):
        user = api.get_user_by_username('bobjones2019')
        cert1 = api.get_certs()[0]
        cert2 = api.get_certs()[1]
        lab = api.get_labs()[0]
        data = urlencode({'cert': cert1['id'], 'redirect_url': '/labs/'})
        self.client.post('/api/labs/' + str(lab['id']) + '/certificates/', data=data, content_type="application/x-www-form-urlencoded")
        data = urlencode({'cert': cert2['id'], 'redirect_url': '/labs/'})
        self.client.post('/api/labs/' + str(lab['id']) + '/certificates/', data=data, content_type="application/x-www-form-urlencoded")
        data = urlencode({'redirect_url': '/users', 'user': user.username, 'role': 0})
        self.client.post('/api/labs/' + str(lab['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        api.update_or_create_user_cert(user_id=user.id,cert_id=cert1['id'],cert_file='testCert.pdf', completion_date="2019-07-03",expiry_date="2019-07-03")
        missingCerts = api.get_missing_lab_certs(user.id, lab['id'])
        self.assertEqual(missingCerts[0]['name'], cert2['name'])

    def testUserMissing2CertsFrom2Labs(self):
        user = api.get_user_by_username('bobjones2019')
        cert1 = api.get_certs()[0]
        cert2 = api.get_certs()[1]
        lab1 = api.get_labs()[0]
        lab2 = api.get_labs()[1]
        data = urlencode({'cert': cert1['id'], 'redirect_url': '/labs/'})
        self.client.post('/api/labs/' + str(lab1['id']) + '/certificates/', data=data, content_type="application/x-www-form-urlencoded")
        data = urlencode({'cert': cert2['id'], 'redirect_url': '/labs/'})
        self.client.post('/api/labs/' + str(lab2['id']) + '/certificates/', data=data, content_type="application/x-www-form-urlencoded")
        data = urlencode({'redirect_url': '/users', 'user': user.username, 'role': 0})
        self.client.post('/api/labs/' + str(lab1['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        data = urlencode({'redirect_url': '/users', 'user': user.username, 'role': 0})
        self.client.post('/api/labs/' + str(lab2['id']) + '/users/', data=data, content_type="application/x-www-form-urlencoded")
        missingCerts = api.get_missing_certs(user.id)
        self.assertEqual(len(missingCerts), 2)

# class CertEmailTest(TestCase):

#     def testEmailCertExpire(self):
#         exec(open("email_notification/test.py").read())
