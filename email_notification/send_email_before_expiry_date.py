from datetime import datetime, timedelta
from cert_tracker_db import CertTrackerDatabase
from send_email_settings import *
from send_email_base import send_email_to_lab_users, send_email_to_pis, send_email_to_admin


# There are two different types of email situations, such as
# 1) lab_user/PI: 1 month prior to expiry date
# 2) admin: 2 weeks before the expiry date
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
                    if 'expiry_date' in cert and 'completion_date' in cert:
                        if cert['expiry_date'] != cert['completion_date'] and cert['expiry_date'] == target_day:
                            lab_user['certs'].add(cert['id'])
                            for pi in lab['pis']:
                                pis[pi].add(user['id'])

            if len(lab_user['certs']) > 0:
                lab_users.append(lab_user)

    return lab_users, pis


def find_users_by_type(users, type):
    """ Find lab users or PIs by type """

    if type == 1:
        target_day = datetime.now() + timedelta(days=DAYS30)
        print("target_day: ", target_day)
        lab_users, pis = find_users_by_days( users, target_day.date() )
        return lab_users, pis

    elif type == 2:
        target_day = datetime.now() + timedelta(days=DAYS14)
        print("target_day: ", target_day)
        lab_users, pis = find_users_by_days( users, target_day.date() )
        return lab_users, None


def send_email_30days_before(users, certs, type):
    """ Send an email to lab users and PIs 1 month before the expiry date """

    print("send_email_30days_before")
    lab_users, pis = find_users_by_type(users, 1)
    if len(lab_users) > 0:
        send_email_to_lab_users(users, certs, lab_users, DAYS30, type)

        if len(pis.keys()) > 0:
            send_email_to_pis(users, certs, pis, DAYS30, type)


def send_email_14days_before(users, certs, admin, type):
    """ Send an email to administrators 2 weeks before the expiry date """

    print("send_email_14days_before")
    lab_users, pis, = find_users_by_type(users, 2)
    if len(lab_users) > 0 and len(admin) > 0:
        send_email_to_admin(users, certs, admin, lab_users, DAYS14, type)


if __name__ == "__main__":
    db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
    users = db.get_users()
    certs = db.get_certs()
    admin = db.get_admin()
    send_email_30days_before(users, certs, 'before')
    send_email_14days_before(users, certs, admin, 'before')

    db.close()
