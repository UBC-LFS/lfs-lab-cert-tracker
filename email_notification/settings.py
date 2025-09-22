import os

# Global variables
DAYS30 = 30
DAYS14 = 14
SITE_URL = ''

DATABASE = os.environ['LFS_LAB_CERT_TRACKER_DB_NAME']
USER = os.environ['LFS_LAB_CERT_TRACKER_DB_USER']
PASSWORD = os.environ['LFS_LAB_CERT_TRACKER_DB_PASSWORD']
HOST = os.environ['LFS_LAB_CERT_TRACKER_DB_HOST']
PORT = os.environ['LFS_LAB_CERT_TRACKER_DB_PORT']

SMTP_SERVER = os.environ['LFS_LAB_CERT_TRACKER_EMAIL_HOST']
SENDER = os.environ['LFS_LAB_CERT_TRACKER_EMAIL_FROM']


"""
How to use cron jobs
# List jobs
$ crontab -l

# Open a crontab
$ crontab -e

# Add jobs
00 09 * * * /srv/trms/email_notification/run_everyday.sh
15 09 */15 * * /srv/trms/email_notification/run_every_15days.sh
"""
