from database import CertTrackerDatabase
from settings import USER, PASSWORD, HOST, PORT, DATABASE, SITE_URL
from base import get_receiver, html_template, send_email


# Send an email to persons who have some missing certificates

def get_message_lab_users(certs, user_id, missing_certs):
    certificates = []
    for cert_id in missing_certs:
        certificates.append("<li>" + certs[cert_id]['name'] + "</li>")

    message = '''\
        <p>Our records indicate that you have missing training certification(s) required for each area. Please take a moment to update your records at your earliest convenience. Let us know if you need any assistance.</p>
        <ul>{0}</ul>
        <p>See <a href="{1}/app/users/{2}/report.pdf/">User Report</a></p>
    '''.format("".join(certificates), SITE_URL, user_id)

    return message


def get_message_pis(users, lab_users):
    lab_users_list = []
    for user_id in lab_users:
        lab_users_list.append("<li>" + users[user_id]['first_name'] + " " + users[user_id]['last_name'] + "</li>")

    message = '''\
         <p>Please be advised that the following users have missing required training certification(s) for your area. Kindly review the list and ensure appropriate actions are taken.</p>
        <ul>{0}</ul>
    '''.format( "".join(lab_users_list) )

    return message


def send_email_lab_users(users, certs, lab_users):
    for user in lab_users:
        receiver = get_receiver(users[ user['id'] ])
        message = get_message_lab_users(certs, user['id'], user['missing_certs'])
        template = html_template(users[ user['id'] ]['first_name'], users[ user['id'] ]['last_name'], message)

        send_email(receiver, template)
    
    print( "User: Sent it. Total users: {0}".format(len(lab_users)) )


def send_email_pis(users, pis):
    for id, lab_users in pis.items():
        if len(lab_users) > 0:
            receiver = get_receiver(users[id])
            message = get_message_pis(users, lab_users)
            template = html_template(users[id]['first_name'], users[id]['last_name'], message)

            send_email(receiver, template)
    
    print( "Supervisor: Sent it. Total PIs: {0}".format(len(pis.keys())) )


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
    send_email_lab_users(users, certs, lab_users)
    send_email_pis(users, pis)

    db.close()
