from lfs_lab_cert_tracker.models import UserCert

import argparse
import datetime
import sys

def run(days):
    delta_days = datetime.timedelta(days=int(days))

    now = datetime.datetime.now()
    expiry_date = now + delta_days
    user_certs = UserCert.objects.filter(expiry_date__lte=expiry_date).prefetch_related('user').prefetch_related('cert')

    for uc in user_certs:
        print("expiry:", uc.expiry_date, ", cert:", uc.cert.name, ", first name:", uc.user.first_name, ", last name:", uc.user.last_name, ", email:", uc.user.email)

