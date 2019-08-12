
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

if __name__ == '__main__':
    '''Lab 1: users:11,12,14 pi:4'''
    '''Lab 2: users:13,15    pi:4,5'''
    subprocess.run('python manage.py loaddata test_users')
    subprocess.run('python manage.py loaddata test_certs')
    subprocess.run('python manage.py loaddata test_labs')
    subprocess.run('python manage.py loaddata test_user_certs')
    subprocess.run('python manage.py loaddata test_user_labs')
    subprocess.run('python manage.py loaddata test_lab_certs')
    unittest.main()