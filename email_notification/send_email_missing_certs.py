from cert_tracker_db import CertTrackerDatabase
from send_email_settings import *
from send_email_base import get_receiver, html_template, send_email

# Send an email to persons who have some missing certificates

def get_message_lab_users(certs, user_id, missing_certs):
    certificates = []
    for cert_id in missing_certs:
        certificates.append("<li>" + certs[cert_id]['name'] + "</li>")

    message = '''\
        <p>You have missing training(s). Please update it.</p>
        <ul>{0}</ul>
        <p>See <a href="{1}/users/{2}/report">User report</a></p>
    '''.format("".join(certificates), LFS_LAB_CERT_TRACKER_URL, user_id)

    return message

def get_message_pis(users, lab_users):
    lab_users_list = []
    for user_id in lab_users:
        lab_users_list.append("<li>" + users[user_id]['first_name'] + " " + users[user_id]['last_name'] + "</li>")

    message = '''\
        <p>The following users have missing training(s).</p>
        <ul>{0}</ul>
    '''.format( "".join(lab_users_list) )

    return message

def send_email_lab_users(users, certs, lab_users):
    for user in lab_users:
        receiver = get_receiver(users[ user['id'] ])
        message = get_message_lab_users(certs, user['id'], user['missing_certs'])
        template = html_template(users[ user['id'] ]['first_name'], users[ user['id'] ]['last_name'], message)

        send_email(receiver, template)
        print( "User: Sent it to {0}".format(receiver) )


def send_email_pis(users, pis):
    for id, lab_users in pis.items():
        if len(lab_users) > 0:
            receiver = get_receiver(users[id])
            message = get_message_pis(users, lab_users)
            template = html_template(users[id]['first_name'], users[id]['last_name'], message)

            send_email(receiver, template)
            print( "Supervisor: Sent it to {0}".format(receiver) )


def find_missing_cert_users(users, certs):
    lab_users = []
    pis = {}

    for id, user in users.items():
        required_certs = set()
        for lab in user['labs']:
            for pi in lab['pis']:
                if not pi in pis:
                    pis[pi] = set()

            for cert in lab['certs']:
                required_certs.add(cert['id'])

        missing_certs = required_certs - user['uploaded_certs']
        if len(missing_certs) > 0:
            lab_users.append({ 'id': id, 'missing_certs': list(missing_certs) })

            for lab in user['labs']:
                for cert in lab['certs']:
                    if cert['id'] in list(missing_certs):
                        for pi in lab['pis']: pis[pi].add(id)

    return lab_users, pis


if __name__ == "__main__":
    db = CertTrackerDatabase(USER, PASSWORD, HOST, PORT, DATABASE)
    users = db.get_users()
    certs = db.get_certs()
    admin = db.get_admin()

    lab_users, pis = find_missing_cert_users(users, certs)
    #send_email_lab_users(users, certs, lab_users)
    #send_email_pis(users, pis)

    db.close()
