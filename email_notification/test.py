
from mock import patch, call
import unittest
import smtplib
from send_email_after_expiry_date import *
from send_email_settings import *
from send_email_before_expiry_date import find_users_by_type
import subprocess
from cert_tracker_db import CertTrackerDatabase
from datetime import datetime, timedelta
import json


class CertExpiryTests(unittest.TestCase):

    def test_find_users_by_days_no_users(self):
        '''Testing where there are no users with expired certifications'''
        db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
        users = db.get_users()
        date = datetime(2019,5,29)
        lab_users, pis = find_users_by_days(users,date.date())
        self.assertEqual(len(lab_users), 0)

    def test_find_users_by_days_1_user(self):
        '''Testing where there 1 lab user with an expired certification and 1 pi in lab'''
        db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
        users = db.get_users()
        date = datetime(2019,5,30)
        lab_users, pis = find_users_by_days(users,date.date())
        self.assertEqual(len(lab_users), 1)
        self.assertEqual(len(pis[4]), 1)
        self.assertEqual(list(pis.keys())[0],4)

    def test_find_users_by_days_multiple_users(self):
        '''Testing 2 users with expired certification and 1 pi in lab'''
        db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
        users = db.get_users()
        date = datetime(2019,5,31)
        lab_users, pis = find_users_by_days(users,date.date())
        self.assertEqual(len(lab_users), 2)
        self.assertEqual(len(pis[4]), 2)
        self.assertEqual(list(pis.keys())[0],4) # pi is 4
    
    def test_find_users_by_days_multiple_pis(self):
        '''Testing 1 user with expired certification and 2 pis in lab'''
        db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
        users = db.get_users()
        date = datetime(2019,6,1)
        lab_users, pis = find_users_by_days(users,date.date())
        self.assertEqual(len(lab_users), 3)
        self.assertEqual(len(pis[4]), 3)
        self.assertEqual(len(pis[5]), 1)

    def test_find_users_by_days_user_in_multiple_labs(self):
        '''Testing 1 user with expired certification involved in 2 labs'''
        db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
        users = db.get_users()
        date = datetime(2019,6,2)
        lab_users, pis = find_users_by_days(users,date.date())
        self.assertEqual(len(lab_users), 4)
        self.assertEqual(len(pis[4]), 4)
        self.assertEqual(len(pis[5]), 2)

    def test_find_users_by_days_user_with_multiple_certs_1_lab(self):
        '''Testing 1 user with 2 expired certifications in 1 lab'''
        db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
        users = db.get_users()
        date = datetime(2019,6,3)
        lab_users, pis = find_users_by_days(users,date.date())
        self.assertEqual(len(lab_users), 5)
        self.assertEqual(len(pis[6]),1)

    def test_find_users_by_day_multiple_labs_and_certs(self):
        '''Testing users with expired certs in 2 seperate labs'''
        db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
        users = db.get_users()
        date = datetime(2019,6,4)
        lab_users, pis = find_users_by_days(users,date.date())
        self.assertEqual(len(lab_users), 6)

    def test_find_user_by_day_inactive_user(self):
        '''Testing inactive user with expired certs'''
        db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
        users = db.get_users()
        date = datetime(2019,6,5)
        lab_users, pis = find_users_by_days(users,date.date())
        self.assertEqual(len(lab_users), 6)

    def test_find_users_by_type_30_days_no_users(self):
        '''Testing where no users have certifications expiring in 30 days'''
        db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
        users = db.get_users()
        lab_users, pis = find_users_by_type(users,1)
        self.assertEqual(len(lab_users),0)

    def test_find_users_by_type_30_days_1_user(self):
        '''Testing 1 user with certification expiring in 30 days'''
        with open('lfs_lab_cert_tracker/fixtures/test_user_certs.json') as f:
            d = json.load(f)
            dateExpire = datetime.now() + timedelta(days=30)
            dateCompletion = datetime.now() + timedelta(days=30) - timedelta(days=1825)
            data = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 17,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 14,
                    "user_id": 14,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            d.append(data)
            json_data = json.dumps(d)
            with open('lfs_lab_cert_tracker/fixtures/test_user_certs2.json', 'w') as g:
                json.dump(d,g)
            subprocess.run('python manage.py loaddata test_user_certs2')
            db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
            users = db.get_users()
            lab_users, pis = find_users_by_type(users,1)
            self.assertEqual(len(lab_users),1)
            self.assertEqual(len(pis[4]),1)
            dateExpire = datetime.now() + timedelta(days=365)
            dateCompletion = datetime.now() + timedelta(days=365) - timedelta(days=1825)
            data = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 17,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 14,
                    "user_id": 14,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            d.append(data)
            json_data = json.dumps(d)
            with open('lfs_lab_cert_tracker/fixtures/test_user_certs2.json', 'w') as g:
                json.dump(d,g)
            subprocess.run('python manage.py loaddata test_user_certs2')

        
    def test_find_users_by_type_30_days_multiple_users(self):
        '''Testing multiple users with certifications expiring in 30 days'''
        with open('lfs_lab_cert_tracker/fixtures/test_user_certs.json') as f:
            d = json.load(f)
            dateExpire = datetime.now() + timedelta(days=30)
            dateCompletion = datetime.now() + timedelta(days=30) - timedelta(days=1825)
            data1 = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 17,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 14,
                    "user_id": 14,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            data2 = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 18,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 14,
                    "user_id": 15,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            d.append(data1)
            d.append(data2)
            json_data = json.dumps(d)
            with open('lfs_lab_cert_tracker/fixtures/test_user_certs2.json', 'w') as g:
                json.dump(d,g)
            subprocess.run('python manage.py loaddata test_user_certs2')
            db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
            users = db.get_users()
            lab_users, pis = find_users_by_type(users,1)
            self.assertEqual(len(lab_users),2)
            self.assertEqual(len(pis[4]),2)
            self.assertEqual(len(pis[5]),1)
            dateExpire = datetime.now() + timedelta(days=365)
            dateCompletion = datetime.now() + timedelta(days=365) - timedelta(days=1825)
            data1 = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 17,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 14,
                    "user_id": 14,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            data2 = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 18,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 14,
                    "user_id": 15,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            d.append(data1)
            d.append(data2)
            json_data = json.dumps(d)
            with open('lfs_lab_cert_tracker/fixtures/test_user_certs2.json', 'w') as g:
                json.dump(d,g)
            subprocess.run('python manage.py loaddata test_user_certs2')

    def test_find_users_by_type_30_days_multiple_pis(self):
        '''Testing user with certification expiring in 30 days with 2 pis in lab'''
        with open('lfs_lab_cert_tracker/fixtures/test_user_certs.json') as f:
            d = json.load(f)
            dateExpire = datetime.now() + timedelta(days=30)
            dateCompletion = datetime.now() + timedelta(days=30) - timedelta(days=1825)
            data1 = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 23,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 14,
                    "user_id": 21,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            d.append(data1)
            json_data = json.dumps(d)
            with open('lfs_lab_cert_tracker/fixtures/test_user_certs2.json', 'w') as g:
                json.dump(d,g)
            subprocess.run('python manage.py loaddata test_user_certs2')
            db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
            users = db.get_users()
            lab_users, pis = find_users_by_type(users,1)
            self.assertEqual(len(lab_users),1)
            self.assertEqual(len(pis[4]),1)
            self.assertEqual(len(pis[5]),1)
            dateExpire = datetime.now() + timedelta(days=365)
            dateCompletion = datetime.now() + timedelta(days=365) - timedelta(days=1825)
            data1 = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 23,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 14,
                    "user_id": 21,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            d.append(data1)
            json_data = json.dumps(d)
            with open('lfs_lab_cert_tracker/fixtures/test_user_certs2.json', 'w') as g:
                json.dump(d,g)
            subprocess.run('python manage.py loaddata test_user_certs2')

    def test_find_users_by_type_30_days_inactive_user(self):
        '''Testing user with certification expiring in 30 days with 2 pis in lab'''
        with open('lfs_lab_cert_tracker/fixtures/test_user_certs.json') as f:
            d = json.load(f)
            dateExpire = datetime.now() + timedelta(days=30)
            dateCompletion = datetime.now() + timedelta(days=30) - timedelta(days=1825)
            data1 = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 24,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 14,
                    "user_id": 23,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            d.append(data1)
            json_data = json.dumps(d)
            with open('lfs_lab_cert_tracker/fixtures/test_user_certs2.json', 'w') as g:
                json.dump(d,g)
            subprocess.run('python manage.py loaddata test_user_certs2')
            db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
            users = db.get_users()
            lab_users, pis = find_users_by_type(users,1)
            self.assertEqual(len(lab_users),0)
            dateExpire = datetime.now() + timedelta(days=365)
            dateCompletion = datetime.now() + timedelta(days=365) - timedelta(days=1825)
            data1 = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 24,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 14,
                    "user_id": 23,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            d.append(data1)
            json_data = json.dumps(d)
            with open('lfs_lab_cert_tracker/fixtures/test_user_certs2.json', 'w') as g:
                json.dump(d,g)
            subprocess.run('python manage.py loaddata test_user_certs2')

    def test_find_users_by_type_30_days_inactive_user(self):
        '''Testing inactive user with cert expiring in 30 days'''
        with open('lfs_lab_cert_tracker/fixtures/test_user_certs.json') as f:
            d = json.load(f)
            dateExpire = datetime.now() + timedelta(days=30)
            dateCompletion = datetime.now() + timedelta(days=30) - timedelta(days=1825)
            data1 = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 24,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 14,
                    "user_id": 23,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            d.append(data1)
            json_data = json.dumps(d)
            with open('lfs_lab_cert_tracker/fixtures/test_user_certs2.json', 'w') as g:
                json.dump(d,g)
            subprocess.run('python manage.py loaddata test_user_certs2')
            db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
            users = db.get_users()
            lab_users, pis = find_users_by_type(users,1)
            self.assertEqual(len(lab_users),0)
            dateExpire = datetime.now() + timedelta(days=365)
            dateCompletion = datetime.now() + timedelta(days=365) - timedelta(days=1825)
            data1 = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 24,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 14,
                    "user_id": 23,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            d.append(data1)
            json_data = json.dumps(d)
            with open('lfs_lab_cert_tracker/fixtures/test_user_certs2.json', 'w') as g:
                json.dump(d,g)
            subprocess.run('python manage.py loaddata test_user_certs2')

    def test_find_users_by_type_14_days_no_users(self):
        '''Testing where no users have certifications expiring in 14 days'''
        db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
        users = db.get_users()
        lab_users, pis = find_users_by_type(users,2)
        self.assertEqual(len(lab_users),0)
        self.assertEqual(pis,None)

    def test_find_users_by_type_14_days_1_user(self):
        '''Testing 1 user with certification expiring in 14 days'''
        with open('lfs_lab_cert_tracker/fixtures/test_user_certs.json') as f:
            d = json.load(f)
            dateExpire = datetime.now() + timedelta(days=14)
            dateCompletion = datetime.now() + timedelta(days=14) - timedelta(days=1825)
            data = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 20,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 14,
                    "user_id": 17,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            d.append(data)
            json_data = json.dumps(d)
            with open('lfs_lab_cert_tracker/fixtures/test_user_certs2.json', 'w') as g:
                json.dump(d,g)
            subprocess.run('python manage.py loaddata test_user_certs2')
            db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
            users = db.get_users()
            lab_users, pis = find_users_by_type(users,2)
            self.assertEqual(len(lab_users),1)
            self.assertEqual(pis,None)
            dateExpire = datetime.now() + timedelta(days=365)
            dateCompletion = datetime.now() + timedelta(days=365) - timedelta(days=1825)
            data = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 20,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 14,
                    "user_id": 17,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            d.append(data)
            json_data = json.dumps(d)
            with open('lfs_lab_cert_tracker/fixtures/test_user_certs2.json', 'w') as g:
                json.dump(d,g)
            subprocess.run('python manage.py loaddata test_user_certs2')

    def test_find_users_by_type_14_days_multiple_users(self):
        '''Testing multiple users with certifications expiring in 14 days'''
        with open('lfs_lab_cert_tracker/fixtures/test_user_certs.json') as f:
            d = json.load(f)
            dateExpire = datetime.now() + timedelta(days=14)
            dateCompletion = datetime.now() + timedelta(days=14) - timedelta(days=1825)
            data1 = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 20,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 14,
                    "user_id": 17,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            data2 = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 21,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 14,
                    "user_id": 18,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            d.append(data1)
            d.append(data2)
            json_data = json.dumps(d)
            with open('lfs_lab_cert_tracker/fixtures/test_user_certs2.json', 'w') as g:
                json.dump(d,g)
            subprocess.run('python manage.py loaddata test_user_certs2')
            db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
            users = db.get_users()
            lab_users, pis = find_users_by_type(users,2)
            self.assertEqual(len(lab_users),2)
            self.assertEqual(pis,None)
            dateExpire = datetime.now() + timedelta(days=365)
            dateCompletion = datetime.now() + timedelta(days=365) - timedelta(days=1825)
            data1 = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 20,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 14,
                    "user_id": 17,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            data2 = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 21,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 14,
                    "user_id": 18,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            d.append(data1)
            d.append(data2)
            json_data = json.dumps(d)
            with open('lfs_lab_cert_tracker/fixtures/test_user_certs2.json', 'w') as g:
                json.dump(d,g)
            subprocess.run('python manage.py loaddata test_user_certs2')

    def test_find_users_by_type_14_days_inactive_user(self):
        '''Testing inactive user with certification expiring in 14 days'''
        with open('lfs_lab_cert_tracker/fixtures/test_user_certs.json') as f:
            d = json.load(f)
            dateExpire = datetime.now() + timedelta(days=14)
            dateCompletion = datetime.now() + timedelta(days=14) - timedelta(days=1825)
            data1 = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 25,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 15,
                    "user_id": 23,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            d.append(data1)
            json_data = json.dumps(d)
            with open('lfs_lab_cert_tracker/fixtures/test_user_certs2.json', 'w') as g:
                json.dump(d,g)
            subprocess.run('python manage.py loaddata test_user_certs2')
            db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
            users = db.get_users()
            lab_users, pis = find_users_by_type(users,2)
            self.assertEqual(len(lab_users),0)
            dateExpire = datetime.now() + timedelta(days=365)
            dateCompletion = datetime.now() + timedelta(days=365) - timedelta(days=1825)
            data1 = {
                "model": "lfs_lab_cert_tracker.usercert",
                "pk": 24,
                "fields": {
                    "expiry_date": dateExpire.strftime('%Y-%m-%d'),
                    "cert_id": 15,
                    "user_id": 23,
                    "cert_file": "users/5/certificates/23/certificate_1.jpg",
                    "uploaded_date": "2018-06-11",
                    "completion_date": dateCompletion.strftime('%Y-%m-%d')
                }
            }
            d.append(data1)
            json_data = json.dumps(d)
            with open('lfs_lab_cert_tracker/fixtures/test_user_certs2.json', 'w') as g:
                json.dump(d,g)
            subprocess.run('python manage.py loaddata test_user_certs2')

if __name__ == '__main__':
    '''How to run tests:'''
    '''1) On Command Prompt go to lfs-lab-cert-tracker directory'''
    '''2) run python email_notification/test.py'''

    '''Lab 1: users:11,12,14,16 pi:4   certs:14'''
    '''Lab 2: users:13,15,16,22 pi:4,5 certs:14'''
    '''Lab 3: users:20          pi:    certs:14,15'''
    '''Lab 4: users:22          pi:    certs:15'''
    '''Admin:1,2,3'''
    '''User 4:              labs:1,2'''
    '''User 5:              labs:2'''
    '''User 11: certs:14    labs:1'''
    '''User 12: certs:14    labs:1'''
    '''User 13: certs:14    labs:2'''
    '''User 14:             labs:1'''
    '''User 15:             labs:2'''
    '''User 16:             labs:1,2'''
    '''User 20: certs:14,15 labs:3'''
    '''User 22: certs:14,15 labs:2,4'''
    subprocess.run('python manage.py loaddata test_users')
    subprocess.run('python manage.py loaddata test_certs')
    subprocess.run('python manage.py loaddata test_labs')
    subprocess.run('python manage.py loaddata test_user_certs')
    subprocess.run('python manage.py loaddata test_user_labs')
    subprocess.run('python manage.py loaddata test_lab_certs')
    unittest.main()