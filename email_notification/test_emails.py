import unittest
from datetime import datetime as dt
import datetime

from cert_tracker_db import CertTrackerDatabase
from send_email_settings import *
from send_email_before_expiry_date import find_users_by_days
from send_email_missing_certs import find_missing_cert_users

class EmailReminderTest(unittest.TestCase):

    def test_missing_certs(self):
        print('Test: Remind missing certs')
        db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
        users = db.get_users()
        certs = db.get_certs()

        lab_users, pis = find_missing_cert_users(users, certs)
        
        self.assertEqual(lab_users[0]['id'], 4)
        self.assertEqual(lab_users[0]['missing_certs'], [1, 2, 3, 5, 15, 16, 20, 22])

        self.assertEqual(lab_users[1]['id'], 5)
        self.assertEqual(lab_users[1]['missing_certs'], [3, 5, 15, 16, 20, 22])

        self.assertEqual(lab_users[2]['id'], 6)
        self.assertEqual(lab_users[2]['missing_certs'], [16, 1, 2, 20])

        self.assertEqual(lab_users[3]['id'], 11)
        self.assertEqual(lab_users[3]['missing_certs'], [2, 5, 15])

        self.assertEqual(lab_users[4]['id'], 13)
        self.assertEqual(lab_users[4]['missing_certs'], [2, 5, 15, 16, 22])

        self.assertEqual(lab_users[5]['id'], 15)
        self.assertEqual(lab_users[5]['missing_certs'], [1, 2, 3, 5, 15, 22])

        self.assertEqual(pis[4], {4, 5, 11, 13, 15})
        self.assertEqual(pis[5], {4, 5, 11, 13, 15})
        self.assertEqual(pis[6], {11, 6})


    def test_before_expiry_date(self):
        print('Test: Remind before expiry date')
        db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
        users = db.get_users()
        admin = db.get_admin()

        self.assertEqual(admin, {1, 2, 3})

        # with no expiry date certs
        target_day1 = dt(2014, 8, 15)
        lab_users, pis = find_users_by_days(users, target_day1.date(), 'before')
        self.assertEqual(lab_users, [])

        self.assertEqual(pis[4][11], [])
        self.assertEqual(pis[4][13], [])
        self.assertEqual(pis[4][15], [])

        self.assertEqual(pis[5][11], [])
        self.assertEqual(pis[5][13], [])
        self.assertEqual(pis[5][15], [])

        self.assertEqual(pis[6][11], [])

        # with expiry date certs
        target_day2 = dt(2019, 7, 13)
        lab_users, pis = find_users_by_days(users, target_day2.date(), 'before')
        self.assertEqual(lab_users[0]['id'], 13)
        self.assertEqual(lab_users[0]['certs'][0], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 7, 13), 'completion_date': datetime.date(2014, 7, 13)})

        self.assertEqual(pis[4][11], [])
        self.assertEqual(pis[4][13][0], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 7, 13), 'completion_date': datetime.date(2014, 7, 13)})
        self.assertEqual(pis[4][15], [])

        self.assertEqual(pis[5][11], [])
        self.assertEqual(pis[5][13][0], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 7, 13), 'completion_date': datetime.date(2014, 7, 13)})
        self.assertEqual(pis[4][15], [])

        self.assertEqual(pis[6][11], [])

        target_day3 = dt(2019, 7, 14)
        lab_users, pis = find_users_by_days(users, target_day3.date(), 'before')
        self.assertEqual(lab_users[0]['id'], 11)
        self.assertEqual(lab_users[0]['certs'][0], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 7, 14), 'completion_date': datetime.date(2014, 7, 14)})

        self.assertEqual(pis[4][11], [{'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 7, 14), 'completion_date': datetime.date(2014, 7, 14)}])
        self.assertEqual(pis[4][13], [])
        self.assertEqual(pis[4][15], [])

        self.assertEqual(pis[5][11][0], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 7, 14), 'completion_date': datetime.date(2014, 7, 14)})
        self.assertEqual(pis[5][13], [])
        self.assertEqual(pis[4][15], [])

        self.assertEqual(pis[6][11][0], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 7, 14), 'completion_date': datetime.date(2014, 7, 14)})


    def test_after_expiry_date(self):
        print('Test: Remind after expiry date')
        db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
        users = db.get_users()
        admin = db.get_admin()

        self.assertEqual(admin, {1, 2, 3})

        target_day1 = dt(2019, 5, 30)
        lab_users, pis = find_users_by_days(users, target_day1.date(), 'after')
        self.assertEqual(lab_users[0]['id'], 15)
        self.assertEqual(lab_users[0]['certs'][0], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 5, 29), 'completion_date': datetime.date(2014, 5, 29)})

        self.assertEqual(pis[4][11], [])
        self.assertEqual(pis[4][13], [])
        self.assertEqual(pis[4][15][0], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 5, 29), 'completion_date': datetime.date(2014, 5, 29)})

        self.assertEqual(pis[5][11], [])
        self.assertEqual(pis[5][13], [])
        self.assertEqual(pis[5][15][0], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 5, 29), 'completion_date': datetime.date(2014, 5, 29)})

        self.assertEqual(pis[6][11], [])


        target_day2 = dt(2019, 6, 30)
        lab_users, pis = find_users_by_days(users, target_day2.date(), 'after')
        self.assertEqual(lab_users[0]['id'], 15)
        self.assertEqual(lab_users[0]['certs'][0], {'id': 16, 'name': 'Biological Safety Course', 'expiry_date': datetime.date(2019, 6, 27), 'completion_date': datetime.date(2014, 6, 27)})
        self.assertEqual(lab_users[0]['certs'][1], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 5, 29), 'completion_date': datetime.date(2014, 5, 29)})

        self.assertEqual(pis[4][11], [])
        self.assertEqual(pis[4][13], [])
        self.assertEqual(pis[4][15][0], {'id': 16, 'name': 'Biological Safety Course', 'expiry_date': datetime.date(2019, 6, 27), 'completion_date': datetime.date(2014, 6, 27)})
        self.assertEqual(pis[4][15][1], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 5, 29), 'completion_date': datetime.date(2014, 5, 29)})

        self.assertEqual(pis[5][11], [])
        self.assertEqual(pis[5][13], [])
        self.assertEqual(pis[5][15][0], {'id': 16, 'name': 'Biological Safety Course', 'expiry_date': datetime.date(2019, 6, 27), 'completion_date': datetime.date(2014, 6, 27)})
        self.assertEqual(pis[5][15][1], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 5, 29), 'completion_date': datetime.date(2014, 5, 29)})

        self.assertEqual(pis[6][11], [])


        target_day3 = dt(2019, 7, 14)
        lab_users, pis = find_users_by_days(users, target_day3.date(), 'after')
        self.assertEqual(lab_users[0]['id'], 13)
        self.assertEqual(lab_users[0]['certs'][0], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 7, 13), 'completion_date': datetime.date(2014, 7, 13)})

        self.assertEqual(lab_users[1]['id'], 15)
        self.assertEqual(lab_users[1]['certs'][0], {'id': 16, 'name': 'Biological Safety Course', 'expiry_date': datetime.date(2019, 6, 27), 'completion_date': datetime.date(2014, 6, 27)})
        self.assertEqual(lab_users[1]['certs'][1], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 5, 29), 'completion_date': datetime.date(2014, 5, 29)})

        self.assertEqual(pis[4][11], [])
        self.assertEqual(pis[4][13][0], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 7, 13), 'completion_date': datetime.date(2014, 7, 13)})
        self.assertEqual(pis[4][15][0], {'id': 16, 'name': 'Biological Safety Course', 'expiry_date': datetime.date(2019, 6, 27), 'completion_date': datetime.date(2014, 6, 27)})
        self.assertEqual(pis[4][15][1], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 5, 29), 'completion_date': datetime.date(2014, 5, 29)})

        self.assertEqual(pis[5][11], [])
        self.assertEqual(pis[5][13][0], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 7, 13), 'completion_date': datetime.date(2014, 7, 13)})
        self.assertEqual(pis[5][15][0], {'id': 16, 'name': 'Biological Safety Course', 'expiry_date': datetime.date(2019, 6, 27), 'completion_date': datetime.date(2014, 6, 27)})
        self.assertEqual(pis[5][15][1], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 5, 29), 'completion_date': datetime.date(2014, 5, 29)})

        self.assertEqual(pis[6][11], [])

        target_day4 = dt(2020, 1, 1)
        lab_users, pis = find_users_by_days(users, target_day4.date(), 'after')
        self.assertEqual(lab_users[0]['id'], 11)
        self.assertEqual(lab_users[0]['certs'][0], {'id': 16, 'name': 'Biological Safety Course', 'expiry_date': datetime.date(2019, 10, 1), 'completion_date': datetime.date(2014, 10, 1)})
        self.assertEqual(lab_users[0]['certs'][1], {'id': 22, 'name': 'Transportation of Dangerous Goods Class 7 (Radioactivity) Receiving Course for ground', 'expiry_date': datetime.date(2019, 10, 1), 'completion_date': datetime.date(2016, 10, 1)})
        self.assertEqual(lab_users[0]['certs'][2], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 7, 14), 'completion_date': datetime.date(2014, 7, 14)})

        self.assertEqual(lab_users[1]['id'], 13)
        self.assertEqual(lab_users[1]['certs'][0], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 7, 13), 'completion_date': datetime.date(2014, 7, 13)})

        self.assertEqual(lab_users[2]['id'], 15)
        self.assertEqual(lab_users[2]['certs'][0], {'id': 16, 'name': 'Biological Safety Course', 'expiry_date': datetime.date(2019, 6, 27), 'completion_date': datetime.date(2014, 6, 27)})
        self.assertEqual(lab_users[2]['certs'][1], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 5, 29), 'completion_date': datetime.date(2014, 5, 29)})

        self.assertEqual(pis[4][11][0], {'id': 16, 'name': 'Biological Safety Course', 'expiry_date': datetime.date(2019, 10, 1), 'completion_date': datetime.date(2014, 10, 1)})
        self.assertEqual(pis[4][11][1], {'id': 22, 'name': 'Transportation of Dangerous Goods Class 7 (Radioactivity) Receiving Course for ground', 'expiry_date': datetime.date(2019, 10, 1), 'completion_date': datetime.date(2016, 10, 1)})
        self.assertEqual(pis[4][11][2], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 7, 14), 'completion_date': datetime.date(2014, 7, 14)})

        self.assertEqual(pis[4][13][0], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 7, 13), 'completion_date': datetime.date(2014, 7, 13)})

        self.assertEqual(pis[4][15][0], {'id': 16, 'name': 'Biological Safety Course', 'expiry_date': datetime.date(2019, 6, 27), 'completion_date': datetime.date(2014, 6, 27)})
        self.assertEqual(pis[4][15][1], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 5, 29), 'completion_date': datetime.date(2014, 5, 29)})

        self.assertEqual(pis[5][11][0], {'id': 16, 'name': 'Biological Safety Course', 'expiry_date': datetime.date(2019, 10, 1), 'completion_date': datetime.date(2014, 10, 1)})
        self.assertEqual(pis[5][11][1], {'id': 22, 'name': 'Transportation of Dangerous Goods Class 7 (Radioactivity) Receiving Course for ground', 'expiry_date': datetime.date(2019, 10, 1), 'completion_date': datetime.date(2016, 10, 1)})
        self.assertEqual(pis[5][11][2], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 7, 14), 'completion_date': datetime.date(2014, 7, 14)})

        self.assertEqual(pis[5][13][0], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 7, 13), 'completion_date': datetime.date(2014, 7, 13)})

        self.assertEqual(pis[5][15][0], {'id': 16, 'name': 'Biological Safety Course', 'expiry_date': datetime.date(2019, 6, 27), 'completion_date': datetime.date(2014, 6, 27)})
        self.assertEqual(pis[5][15][1], {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 5, 29), 'completion_date': datetime.date(2014, 5, 29)})

        self.assertEqual(pis[6][11][0], {'id': 16, 'name': 'Biological Safety Course', 'expiry_date': datetime.date(2019, 10, 1), 'completion_date': datetime.date(2014, 10, 1)}, {'id': 20, 'name': 'Biosafety for Permit Holders', 'expiry_date': datetime.date(2019, 7, 14), 'completion_date': datetime.date(2014, 7, 14)})


if __name__ == '__main__':

    unittest.main()
