from datetime import datetime, timedelta
from cert_tracker_db import CertTrackerDatabase
from send_email_settings import *
from send_email_base import send_email_to_lab_users, send_email_to_pis, send_email_to_admin


# There are two different types of an email remider, such as
# 1) lab_user/PI: 1 month prior to expiry date
# 2) admin: 2 weeks before the expiry date
# Note: PI means Principal Investigator


def find_users_by_days(users, target_day, type):
    """ Find lab users and PIs who have any certificates to be expired in a target day """

    lab_users = []
    pis = {}
    for uid, user in users.items():
        if user['has_expiry_cert'] == True:
            lab_user = {'id': user['id'], 'certs': []}

            for lab in user['labs']:
                for pi in lab['pis']:
                    if pi not in pis: pis[pi] = dict()
                    if uid not in pis[pi]: pis[pi][uid] = []

                    for cert in lab['certs']:
                        if 'expiry_date' in cert and 'completion_date' in cert and cert['expiry_date'] != cert['completion_date']:
                            if type == 'before':
                                if cert['expiry_date'] == target_day:
                                    if contain_cert(lab_user['certs'], cert['id']) == False:
                                        lab_user['certs'].append(cert)

                                    pis[pi][uid].append(cert)
                            elif type == 'after':
                                if cert['expiry_date'] < target_day:
                                    if contain_cert(lab_user['certs'], cert['id']) == False:
                                        lab_user['certs'].append(cert)

                                    pis[pi][uid].append(cert)

            if len(lab_user['certs']) > 0:
                lab_users.append(lab_user)

    return lab_users, pis

def find_users_by_type(users, type):
    """ Find lab users or PIs by type """

    if type == 1:
        target_day = datetime.now() + timedelta(days=DAYS30)
        print("target_day: ", target_day)
        lab_users, pis = find_users_by_days(users, target_day.date(), 'before')
        return lab_users, pis

    elif type == 2:
        target_day = datetime.now() + timedelta(days=DAYS14)
        print("target_day: ", target_day)
        lab_users, pis = find_users_by_days(users, target_day.date(), 'before')
        return lab_users, None


def send_email_30days_before(users, certs, type):
    """ Send an email to lab users and PIs 1 month before the expiry date """

    print("Send email 30days before")
    lab_users, pis = find_users_by_type(users, 1)
    if len(lab_users) > 0:
        send_email_to_lab_users(users, lab_users, DAYS30, type)

        if len(pis.keys()) > 0:
            send_email_to_pis(users, pis, DAYS30, type)


def send_email_14days_before(users, certs, admin, type):
    """ Send an email to administrators 2 weeks before the expiry date """

    print("send email 14days before")
    lab_users, pis, = find_users_by_type(users, 2)
    if len(lab_users) > 0 and len(admin) > 0:
        send_email_to_admin(users, admin, lab_users, DAYS14, type)


# Helper functions

def contain_cert(certs, cert_id):
    """ Check whether user's certs contain a cert """

    for cert in certs:
        if cert['id'] == cert_id:
            return True

    return False


if __name__ == "__main__":
    db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
    users = db.get_users()
    certs = db.get_certs()
    admin = db.get_admin()
    send_email_30days_before(users, certs, 'before')
    send_email_14days_before(users, certs, admin, 'before')

    db.close()
