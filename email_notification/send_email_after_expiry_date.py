from datetime import datetime
from cert_tracker_db import CertTrackerDatabase
from send_email_settings import *
from send_email_base import send_email_to_lab_users, send_email_to_pis, send_email_to_admin


# It will keep sending an email to users (Admins, PIs, Lab Users)
# after the expiry date every twice a month
# Note: PI means Principal Investigator

def find_users_by_days(users, target_day):
    """ Find lab users and PIs who have any certificates to be expired
    in a target day """

    lab_users = []
    pis = {}
    for id, user in users.items():
        if user['has_expiry_cert'] == True:
            lab_user = { 'id': user['id'], 'certs': set() }

            for lab in user['labs']:
                for pi in lab['pis']:
                    if not pi in pis:
                        pis[pi] = set()

                for cert in lab['certs']:
                    if 'expiry_date' in cert and cert['expiry_date'] < target_day \
                    and 'completion_date' in cert and cert['expiry_date'] != cert['completion_date']:
                        lab_user['certs'].add(cert['id'])
                        for pi in lab['pis']:
                            pis[pi].add(user['id'])

            if len(lab_user['certs']) > 0:
                lab_users.append(lab_user)

    return lab_users, pis


def send_email_after(users, certs, admin, type):
    """ Send an email to lab_users/Pis/admin every twice a month after the expiry date """

    print("send_email_after_expiry")
    target_day = datetime.now()
    lab_users, pis = find_users_by_days(users, target_day.date())

    if len(lab_users) > 0:
        send_email_to_lab_users(users, certs, lab_users, DAYS14, type)

        if len(pis.keys()) > 0:
            send_email_to_pis(users, certs, pis, DAYS14, type)

        if len(admin) > 0:
            send_email_to_admin(users, certs, admin, lab_users, DAYS14, type)


if __name__ == "__main__":
    db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
    users = db.get_users()
    certs = db.get_certs()
    admin = db.get_admin()
    send_email_after(users, certs, admin, 'after')

    db.close()
