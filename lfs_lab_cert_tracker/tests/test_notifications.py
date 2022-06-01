from django.test import TestCase
from django.urls import reverse
from datetime import datetime, timedelta
import datetime as dt

from lfs_lab_cert_tracker.utils import Api, Notification

DATA = [
    'lfs_lab_cert_tracker/fixtures/certs.json',
    'lfs_lab_cert_tracker/fixtures/labs.json',
    'lfs_lab_cert_tracker/fixtures/users.json',
    'lfs_lab_cert_tracker/fixtures/user_certs.json',
    'lfs_lab_cert_tracker/fixtures/user_labs.json',
    'lfs_lab_cert_tracker/fixtures/lab_certs.json'
]


class NotificationTest(TestCase):
    fixtures = DATA

    @classmethod
    def setUpTestData(cls):
        cls.api = Api()
        cls.notification = Notification()

    def test_missing_trainings(self):
        print('\n- Test: missing trainings - check lab users in no supervisors')

        lab_users, pis = self.notification.find_missing_trainings()

        self.assertEqual(lab_users[7]['id'], 30)
        self.assertEqual(lab_users[7]['missing_trainings'], [16])


    def test_missing_trainings(self):
        print('\n- Test: missing trainings')

        lab_users, pis = self.notification.find_missing_trainings()

        # Lab users
        self.assertEqual( len(lab_users), 8 )

        self.assertEqual(lab_users[0]['id'], 4)
        self.assertEqual(lab_users[0]['missing_trainings'], [16, 2, 3, 20, 5, 22, 15])

        self.assertEqual(lab_users[1]['id'], 5)
        self.assertEqual(lab_users[1]['missing_trainings'], [16, 3, 20, 5, 22, 15])

        self.assertEqual(lab_users[2]['id'], 6)
        self.assertEqual(lab_users[2]['missing_trainings'], [16, 1, 2, 20])

        self.assertEqual(lab_users[3]['id'], 11)
        self.assertEqual(lab_users[3]['missing_trainings'], [2, 5, 15])

        self.assertEqual(lab_users[4]['id'], 13)
        self.assertEqual(lab_users[4]['missing_trainings'], [16, 2, 5, 22, 15])

        self.assertEqual(lab_users[5]['id'], 15)
        self.assertEqual(lab_users[5]['missing_trainings'], [1, 2, 3, 5, 22, 15])

        self.assertEqual(lab_users[6]['id'], 20)
        self.assertEqual(lab_users[6]['missing_trainings'], [16, 20])

        # PIs

        self.assertEqual( len(pis.keys()), 4 )
        self.assertEqual(pis[4], {4, 5, 11, 13, 15})
        self.assertEqual(pis[5], {4, 5, 11, 13, 15})
        self.assertEqual(pis[6], {11, 20, 6})
        self.assertEqual(pis[20], set())


    def test_before_expiry_date_day1(self):
        print('\n- Test: Remind before expiry date: 2014-7-17 + 30')

        # with no expiry date certs
        target_day = datetime(2014, 7, 16) + timedelta(30)
        lab_users, pis = self.notification.find_expired_trainings(target_day.date(), 'before')

        self.assertEqual(lab_users, [])
        self.assertEqual(pis, {})


    def test_before_expiry_date_day2(self):
        print('\n- Test: Remind before expiry date: 2019-6-13 + 30')

        # with expiry date certs
        target_day = datetime(2019, 6, 13) + timedelta(30)
        lab_users, pis = self.notification.find_expired_trainings(target_day.date(), 'before')
        self.assertEqual(lab_users[0]['id'], 13)
        self.assertEqual(lab_users[0]['trainings'][0]['id'], 20)
        self.assertEqual(lab_users[0]['trainings'][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(lab_users[0]['trainings'][0]['completion_date'], dt.date(2014, 7, 13))
        self.assertEqual(lab_users[0]['trainings'][0]['expiry_date'], dt.date(2019, 7, 13))

        self.assertEqual(pis[4][13][0]['id'], 20)
        self.assertEqual(pis[4][13][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[4][13][0]['completion_date'], dt.date(2014, 7, 13))
        self.assertEqual(pis[4][13][0]['expiry_date'], dt.date(2019, 7, 13))

        self.assertEqual(pis[5][13][0]['id'], 20)
        self.assertEqual(pis[5][13][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[5][13][0]['completion_date'], dt.date(2014, 7, 13))
        self.assertEqual(pis[5][13][0]['expiry_date'], dt.date(2019, 7, 13))


    def test_before_expiry_date_day3(self):
        print('\n- Test: Remind before expiry date: 2019-6-14 + 30')

        target_day = datetime(2019, 6, 14) + timedelta(30)
        lab_users, pis = self.notification.find_expired_trainings(target_day.date(), 'before')

        self.assertEqual(lab_users[0]['id'], 11)
        self.assertEqual(lab_users[0]['trainings'][0]['id'], 20)
        self.assertEqual(lab_users[0]['trainings'][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(lab_users[0]['trainings'][0]['completion_date'], dt.date(2014, 7, 14))
        self.assertEqual(lab_users[0]['trainings'][0]['expiry_date'], dt.date(2019, 7, 14))

        self.assertEqual(pis[4][11][0]['id'], 20)
        self.assertEqual(pis[4][11][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[4][11][0]['completion_date'], dt.date(2014, 7, 14))
        self.assertEqual(pis[4][11][0]['expiry_date'], dt.date(2019, 7, 14))

        self.assertEqual(pis[5][11][0]['id'], 20)
        self.assertEqual(pis[5][11][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[5][11][0]['completion_date'], dt.date(2014, 7, 14))
        self.assertEqual(pis[5][11][0]['expiry_date'], dt.date(2019, 7, 14))

        self.assertEqual(pis[6][11][0]['id'], 20)
        self.assertEqual(pis[6][11][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[6][11][0]['completion_date'], dt.date(2014, 7, 14))
        self.assertEqual(pis[6][11][0]['expiry_date'], dt.date(2019, 7, 14))


    def test_after_expiry_date_day1(self):
        print('\n- Test: Remind after expiry date: 2019-5-30')

        target_day = datetime(2019, 5, 30)
        lab_users, pis = self.notification.find_expired_trainings(target_day.date(), 'after')

        self.assertEqual(lab_users[0]['id'], 12)
        self.assertEqual(lab_users[0]['trainings'][0]['id'], 16)
        self.assertEqual(lab_users[0]['trainings'][0]['training'].name, 'Biological Safety Course')
        self.assertEqual(lab_users[0]['trainings'][0]['completion_date'], dt.date(2010, 1, 1))
        self.assertEqual(lab_users[0]['trainings'][0]['expiry_date'], dt.date(2015, 1, 1))

        self.assertEqual(lab_users[1]['id'], 15)
        self.assertEqual(lab_users[1]['trainings'][0]['id'], 20)
        self.assertEqual(lab_users[1]['trainings'][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(lab_users[1]['trainings'][0]['completion_date'], dt.date(2014, 5, 29))
        self.assertEqual(lab_users[1]['trainings'][0]['expiry_date'], dt.date(2019, 5, 29))

        self.assertEqual(pis[4][15][0]['id'], 20)
        self.assertEqual(pis[4][15][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[4][15][0]['completion_date'], dt.date(2014, 5, 29))
        self.assertEqual(pis[4][15][0]['expiry_date'], dt.date(2019, 5, 29))

        self.assertEqual(pis[5][15][0]['id'], 20)
        self.assertEqual(pis[5][15][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[5][15][0]['completion_date'], dt.date(2014, 5, 29))
        self.assertEqual(pis[5][15][0]['expiry_date'], dt.date(2019, 5, 29))

    def test_after_expiry_date_day2(self):
        print('\n- Test: Remind after expiry date: 2019-6-30')

        target_day = datetime(2019, 6, 30)
        lab_users, pis = self.notification.find_expired_trainings(target_day.date(), 'after')

        # Lab users

        self.assertEqual(lab_users[0]['id'], 12)
        self.assertEqual(lab_users[0]['trainings'][0]['id'], 16)
        self.assertEqual(lab_users[0]['trainings'][0]['training'].name, 'Biological Safety Course')
        self.assertEqual(lab_users[0]['trainings'][0]['completion_date'], dt.date(2010, 1, 1))
        self.assertEqual(lab_users[0]['trainings'][0]['expiry_date'], dt.date(2015, 1, 1))

        self.assertEqual(lab_users[1]['id'], 15)
        self.assertEqual(lab_users[1]['trainings'][0]['id'], 16)
        self.assertEqual(lab_users[1]['trainings'][0]['training'].name, 'Biological Safety Course')
        self.assertEqual(lab_users[1]['trainings'][0]['completion_date'], dt.date(2014, 6, 27))
        self.assertEqual(lab_users[1]['trainings'][0]['expiry_date'], dt.date(2019, 6, 27))
        self.assertEqual(lab_users[1]['trainings'][1]['id'], 20)
        self.assertEqual(lab_users[1]['trainings'][1]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(lab_users[1]['trainings'][1]['completion_date'], dt.date(2014, 5, 29))
        self.assertEqual(lab_users[1]['trainings'][1]['expiry_date'], dt.date(2019, 5, 29))

        # PIs
        self.assertEqual(pis[4][15][0]['id'], 16)
        self.assertEqual(pis[4][15][0]['training'].name, 'Biological Safety Course')
        self.assertEqual(pis[4][15][0]['completion_date'], dt.date(2014, 6, 27))
        self.assertEqual(pis[4][15][0]['expiry_date'], dt.date(2019, 6, 27))
        self.assertEqual(pis[4][15][1]['id'], 20)
        self.assertEqual(pis[4][15][1]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[4][15][1]['completion_date'], dt.date(2014, 5, 29))
        self.assertEqual(pis[4][15][1]['expiry_date'], dt.date(2019, 5, 29))

        self.assertEqual(pis[5][15][0]['id'], 16)
        self.assertEqual(pis[5][15][0]['training'].name, 'Biological Safety Course')
        self.assertEqual(pis[5][15][0]['completion_date'], dt.date(2014, 6, 27))
        self.assertEqual(pis[5][15][0]['expiry_date'], dt.date(2019, 6, 27))
        self.assertEqual(pis[5][15][1]['id'], 20)
        self.assertEqual(pis[5][15][1]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[5][15][1]['completion_date'], dt.date(2014, 5, 29))
        self.assertEqual(pis[5][15][1]['expiry_date'], dt.date(2019, 5, 29))


    def test_after_expiry_date_day3(self):
        print('\n- Test: Remind after expiry date: 2019-7-14')

        target_day = datetime(2019, 7, 14)
        lab_users, pis = self.notification.find_expired_trainings(target_day.date(), 'after')


        # Lab users

        self.assertEqual(lab_users[0]['id'], 12)
        self.assertEqual(lab_users[0]['trainings'][0]['id'], 16)
        self.assertEqual(lab_users[0]['trainings'][0]['training'].name, 'Biological Safety Course')
        self.assertEqual(lab_users[0]['trainings'][0]['completion_date'], dt.date(2010, 1, 1))
        self.assertEqual(lab_users[0]['trainings'][0]['expiry_date'], dt.date(2015, 1, 1))

        self.assertEqual(lab_users[1]['id'], 13)
        self.assertEqual(lab_users[1]['trainings'][0]['id'], 20)
        self.assertEqual(lab_users[1]['trainings'][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(lab_users[1]['trainings'][0]['completion_date'], dt.date(2014, 7, 13))
        self.assertEqual(lab_users[1]['trainings'][0]['expiry_date'], dt.date(2019, 7, 13))

        self.assertEqual(lab_users[2]['id'], 15)
        self.assertEqual(lab_users[2]['trainings'][0]['id'], 16)
        self.assertEqual(lab_users[2]['trainings'][0]['training'].name, 'Biological Safety Course')
        self.assertEqual(lab_users[2]['trainings'][0]['completion_date'], dt.date(2014, 6, 27))
        self.assertEqual(lab_users[2]['trainings'][0]['expiry_date'], dt.date(2019, 6, 27))
        self.assertEqual(lab_users[2]['trainings'][1]['id'], 20)
        self.assertEqual(lab_users[2]['trainings'][1]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(lab_users[2]['trainings'][1]['completion_date'], dt.date(2014, 5, 29))
        self.assertEqual(lab_users[2]['trainings'][1]['expiry_date'], dt.date(2019, 5, 29))

        # PIs
        self.assertEqual(pis[4][13][0]['id'], 20)
        self.assertEqual(pis[4][13][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[4][13][0]['completion_date'], dt.date(2014, 7, 13))
        self.assertEqual(pis[4][13][0]['expiry_date'], dt.date(2019, 7, 13))

        self.assertEqual(pis[4][15][0]['id'], 16)
        self.assertEqual(pis[4][15][0]['training'].name, 'Biological Safety Course')
        self.assertEqual(pis[4][15][0]['completion_date'], dt.date(2014, 6, 27))
        self.assertEqual(pis[4][15][0]['expiry_date'], dt.date(2019, 6, 27))
        self.assertEqual(pis[4][15][1]['id'], 20)
        self.assertEqual(pis[4][15][1]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[4][15][1]['completion_date'], dt.date(2014, 5, 29))
        self.assertEqual(pis[4][15][1]['expiry_date'], dt.date(2019, 5, 29))

        self.assertEqual(pis[5][13][0]['id'], 20)
        self.assertEqual(pis[5][13][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[5][13][0]['completion_date'], dt.date(2014, 7, 13))
        self.assertEqual(pis[5][13][0]['expiry_date'], dt.date(2019, 7, 13))

        self.assertEqual(pis[5][15][0]['id'], 16)
        self.assertEqual(pis[5][15][0]['training'].name, 'Biological Safety Course')
        self.assertEqual(pis[5][15][0]['completion_date'], dt.date(2014, 6, 27))
        self.assertEqual(pis[5][15][0]['expiry_date'], dt.date(2019, 6, 27))
        self.assertEqual(pis[5][15][1]['id'], 20)
        self.assertEqual(pis[5][15][1]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[5][15][1]['completion_date'], dt.date(2014, 5, 29))
        self.assertEqual(pis[5][15][1]['expiry_date'], dt.date(2019, 5, 29))

    def test_after_expiry_date_day4(self):
        print('\n- Test: Remind after expiry date: 2020-1-1')

        target_day = datetime(2020, 1, 1)
        lab_users, pis = self.notification.find_expired_trainings(target_day.date(), 'after')

        # Lab users
        self.assertEqual(lab_users[0]['id'], 11)

        self.assertEqual(lab_users[0]['trainings'][0]['id'], 20)
        self.assertEqual(lab_users[0]['trainings'][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(lab_users[0]['trainings'][0]['completion_date'], dt.date(2014, 7, 14))
        self.assertEqual(lab_users[0]['trainings'][0]['expiry_date'], dt.date(2019, 7, 14))

        self.assertEqual(lab_users[0]['trainings'][1]['id'], 16)
        self.assertEqual(lab_users[0]['trainings'][1]['training'].name, 'Biological Safety Course')
        self.assertEqual(lab_users[0]['trainings'][1]['completion_date'], dt.date(2014, 10, 1))
        self.assertEqual(lab_users[0]['trainings'][1]['expiry_date'], dt.date(2019, 10, 1))

        self.assertEqual(lab_users[0]['trainings'][2]['id'], 22)
        self.assertEqual(lab_users[0]['trainings'][2]['training'].name, 'Transportation of Dangerous Goods Class 7 (Radioactivity) Receiving Course for ground')
        self.assertEqual(lab_users[0]['trainings'][2]['completion_date'], dt.date(2016, 10, 1))
        self.assertEqual(lab_users[0]['trainings'][2]['expiry_date'], dt.date(2019, 10, 1))

        self.assertEqual(lab_users[1]['id'], 12)
        self.assertEqual(lab_users[1]['trainings'][0]['id'], 16)
        self.assertEqual(lab_users[1]['trainings'][0]['training'].name, 'Biological Safety Course')
        self.assertEqual(lab_users[1]['trainings'][0]['completion_date'], dt.date(2010, 1, 1))
        self.assertEqual(lab_users[1]['trainings'][0]['expiry_date'], dt.date(2015, 1, 1))

        self.assertEqual(lab_users[2]['id'], 13)
        self.assertEqual(lab_users[2]['trainings'][0]['id'], 20)
        self.assertEqual(lab_users[2]['trainings'][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(lab_users[2]['trainings'][0]['completion_date'], dt.date(2014, 7, 13))
        self.assertEqual(lab_users[2]['trainings'][0]['expiry_date'], dt.date(2019, 7, 13))

        self.assertEqual(lab_users[3]['id'], 15)

        self.assertEqual(lab_users[3]['trainings'][0]['id'], 16)
        self.assertEqual(lab_users[3]['trainings'][0]['training'].name, 'Biological Safety Course')
        self.assertEqual(lab_users[3]['trainings'][0]['completion_date'], dt.date(2014, 6, 27))
        self.assertEqual(lab_users[3]['trainings'][0]['expiry_date'], dt.date(2019, 6, 27))

        self.assertEqual(lab_users[3]['trainings'][1]['id'], 20)
        self.assertEqual(lab_users[3]['trainings'][1]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(lab_users[3]['trainings'][1]['completion_date'], dt.date(2014, 5, 29))
        self.assertEqual(lab_users[3]['trainings'][1]['expiry_date'], dt.date(2019, 5, 29))

        # PIs

        self.assertEqual(pis[4][11][0]['id'], 20)
        self.assertEqual(pis[4][11][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[4][11][0]['completion_date'], dt.date(2014, 7, 14))
        self.assertEqual(pis[4][11][0]['expiry_date'], dt.date(2019, 7, 14))

        self.assertEqual(pis[4][11][1]['id'], 16)
        self.assertEqual(pis[4][11][1]['training'].name, 'Biological Safety Course')
        self.assertEqual(pis[4][11][1]['completion_date'], dt.date(2014, 10, 1))
        self.assertEqual(pis[4][11][1]['expiry_date'], dt.date(2019, 10, 1))

        self.assertEqual(pis[4][11][2]['id'], 22)
        self.assertEqual(pis[4][11][2]['training'].name, 'Transportation of Dangerous Goods Class 7 (Radioactivity) Receiving Course for ground')
        self.assertEqual(pis[4][11][2]['completion_date'], dt.date(2016, 10, 1))
        self.assertEqual(pis[4][11][2]['expiry_date'], dt.date(2019, 10, 1))

        self.assertEqual(pis[4][13][0]['id'], 20)
        self.assertEqual(pis[4][13][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[4][13][0]['completion_date'], dt.date(2014, 7, 13))
        self.assertEqual(pis[4][13][0]['expiry_date'], dt.date(2019, 7, 13))

        self.assertEqual(pis[4][15][0]['id'], 16)
        self.assertEqual(pis[4][15][0]['training'].name, 'Biological Safety Course')
        self.assertEqual(pis[4][15][0]['completion_date'], dt.date(2014, 6, 27))
        self.assertEqual(pis[4][15][0]['expiry_date'], dt.date(2019, 6, 27))

        self.assertEqual(pis[4][15][1]['id'], 20)
        self.assertEqual(pis[4][15][1]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[4][15][1]['completion_date'], dt.date(2014, 5, 29))
        self.assertEqual(pis[4][15][1]['expiry_date'], dt.date(2019, 5, 29))


        self.assertEqual(pis[5][11][0]['id'], 20)
        self.assertEqual(pis[5][11][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[5][11][0]['completion_date'], dt.date(2014, 7, 14))
        self.assertEqual(pis[5][11][0]['expiry_date'], dt.date(2019, 7, 14))

        self.assertEqual(pis[5][11][1]['id'], 16)
        self.assertEqual(pis[5][11][1]['training'].name, 'Biological Safety Course')
        self.assertEqual(pis[5][11][1]['completion_date'], dt.date(2014, 10, 1))
        self.assertEqual(pis[5][11][1]['expiry_date'], dt.date(2019, 10, 1))

        self.assertEqual(pis[5][11][2]['id'], 22)
        self.assertEqual(pis[5][11][2]['training'].name, 'Transportation of Dangerous Goods Class 7 (Radioactivity) Receiving Course for ground')
        self.assertEqual(pis[5][11][2]['completion_date'], dt.date(2016, 10, 1))
        self.assertEqual(pis[5][11][2]['expiry_date'], dt.date(2019, 10, 1))

        self.assertEqual(pis[5][13][0]['id'], 20)
        self.assertEqual(pis[5][13][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[5][13][0]['completion_date'], dt.date(2014, 7, 13))
        self.assertEqual(pis[5][13][0]['expiry_date'], dt.date(2019, 7, 13))

        self.assertEqual(pis[5][15][0]['id'], 16)
        self.assertEqual(pis[5][15][0]['training'].name, 'Biological Safety Course')
        self.assertEqual(pis[5][15][0]['completion_date'], dt.date(2014, 6, 27))
        self.assertEqual(pis[5][15][0]['expiry_date'], dt.date(2019, 6, 27))

        self.assertEqual(pis[5][15][1]['id'], 20)
        self.assertEqual(pis[5][15][1]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[5][15][1]['completion_date'], dt.date(2014, 5, 29))
        self.assertEqual(pis[5][15][1]['expiry_date'], dt.date(2019, 5, 29))

        self.assertEqual(pis[6][11][0]['id'], 20)
        self.assertEqual(pis[6][11][0]['training'].name, 'Biosafety for Permit Holders')
        self.assertEqual(pis[6][11][0]['completion_date'], dt.date(2014, 7, 14))
        self.assertEqual(pis[6][11][0]['expiry_date'], dt.date(2019, 7, 14))

        self.assertEqual(pis[6][11][1]['id'], 16)
        self.assertEqual(pis[6][11][1]['training'].name, 'Biological Safety Course')
        self.assertEqual(pis[6][11][1]['completion_date'], dt.date(2014, 10, 1))
        self.assertEqual(pis[6][11][1]['expiry_date'], dt.date(2019, 10, 1))


    def test_after_expiry_date_day5(self):
        print('\n- Test: Remind after expiry date: 2016-01-01 - check lab users in no supervisors')

        target_day = datetime(2016, 1, 1)
        lab_users, pis = self.notification.find_expired_trainings(target_day.date(), 'after')

        self.assertEqual(lab_users[0]['id'], 12)

        self.assertEqual(lab_users[0]['trainings'][0]['id'], 16)
        self.assertEqual(lab_users[0]['trainings'][0]['training'].name, 'Biological Safety Course')
        self.assertEqual(lab_users[0]['trainings'][0]['completion_date'], dt.date(2010, 1, 1))
        self.assertEqual(lab_users[0]['trainings'][0]['expiry_date'], dt.date(2015, 1, 1))

        self.assertEqual(pis, {})
