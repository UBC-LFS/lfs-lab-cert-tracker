from datetime import datetime
from cert_tracker_db import CertTrackerDatabase
from send_email_settings import *
from send_email_base import send_email_to_lab_users, send_email_to_pis, send_email_to_admin
from send_email_before_expiry_date import find_users_by_days

# It will keep sending an email to users (Admins, PIs, Lab Users)
# after the expiry date every twice a month
# Note: PI means Principal Investigator


def send_email_after(users, certs, admin, type):
    """ Send an email to lab_users/Pis/admin every twice a month after the expiry date """

    print("Send email after expiry date")

    target_day = datetime.now()
    print("target_day: ", target_day)

    lab_users, pis = find_users_by_days(users, target_day.date(), 'after')

    if len(lab_users) > 0:
        send_email_to_lab_users(users, lab_users, DAYS14, type)

        if len(pis.keys()) > 0:
            send_email_to_pis(users, pis, DAYS14, type)

        if len(admin) > 0:
            send_email_to_admin(users, admin, lab_users, DAYS14, type)


if __name__ == "__main__":
    db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
    users = db.get_users()
    certs = db.get_certs()
    admin = db.get_admin()
    send_email_after(users, certs, admin, 'after')

    db.close()
