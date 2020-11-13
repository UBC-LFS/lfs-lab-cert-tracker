import unittest
from datetime import datetime

from cert_tracker_db import CertTrackerDatabase
from send_email_settings import *
from send_email_before_expiry_date import find_users_by_days

class EmailReminderTest(unittest.TestCase):
    def test_before_expiry_date(self):
        print('Test: Remind before expiry date')
        db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
        users = db.get_users()
        admin = db.get_admin()

        self.assertEqual(admin, {1, 2, 3})

        # with no expiry date certs
        target_day1 = datetime(2014, 8, 15)
        lab_users, pis = find_users_by_days( users, target_day1.date() )
        self.assertEqual(lab_users, [])
        self.assertEqual(pis, {4: set(), 5: set()})

        # with expiry date certs
        target_day2 = datetime(2019, 7, 13)
        lab_users, pis = find_users_by_days( users, target_day2.date() )
        self.assertEqual(lab_users, [{'id': 11, 'certs': {20}}, {'id': 13, 'certs': {20}}])
        self.assertEqual(pis, {4: {11, 13}, 5: {11, 13}})


if __name__ == '__main__':

    unittest.main()
