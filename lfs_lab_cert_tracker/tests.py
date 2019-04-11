from django.test import TestCase

from lfs_lab_cert_tracker import api

class UserTestCase(TestCase):
    def test_create_user(self):
        user = api.create_user("foo", "bar", "foobar@email.com", "foobar")
        actual = api.get_user_by_cwl("foobar")
        self.assertEqual(user['cwl'], actual.cwl)
        actual = api.get_user_by_cwl("foobar")
        self.assertEqual(user['cwl'], actual.cwl)
