
from mock import patch, call
import unittest
import smtplib
# from email_notification import send_email_base, send_email_settings
import subprocess


class SendEmailTests(unittest.TestCase):

    def test_send_email(self):
        # Mock 'smtplib.SMTP' class
        print('HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH')
        with patch("smtplib.SMTP") as mock_smtp:
            subprocess.call("python email_notification/send_email_after_expiry_date.py", shell=True)
            instance = mock_smtp.return_value
            print('HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH')
            print(self.assertTrue(instance.sendmail.called))

if __name__ == '__main__':
    unittest.main()