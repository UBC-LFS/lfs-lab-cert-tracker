import os
import psycopg2
from datetime import datetime, timedelta
import copy
import smtplib, ssl
from email.mime.text import MIMEText


# There are three types of email situations, such as
# 1) student/PI: 1 month prior to expiry date
# 2) admin: 2 weeks before the expiry date
# 3) student/PI/admin: 2 weeks after the expiry date
#
# Note: PI means Principal Investigator


# Global variables
DAYS30 = 30
DAYS14 = 14
LFS_LAB_CERT_TRACKER_URL = os.environ['LFS_LAB_CERT_TRACKER_URL']

# Helper functions
def change_date_format(date):
    return '{0}-{1}-{2}'.format(date.year, date.month, date.day)


def get_all_users(cursor):
    """ Get all users """

    cursor.execute("SELECT * FROM auth_user;")
    rows = cursor.fetchall()
    users = { 'data': [], 'byId': {} }
    for row in rows:
        id = row[0]
        is_superuser = row[3]
        username = row[4]
        first_name = row[5]
        last_name = row[6]
        email = row[7]
        is_active = row[9]
        user = {
            'id': id,
            'is_superuser': is_superuser,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'is_active': is_active,
            'has_expiry_cert': False,
            'labs': []
        }
        #users['data'].append(user)
        users['byId'][id] = user
    return users


def get_all_labs(cursor):
    """ Get all labs """

    cursor.execute("SELECT * FROM lfs_lab_cert_tracker_lab;")
    rows = cursor.fetchall()
    labs = { 'data': [], 'byId': {} }
    for row in rows:
        id = row[0]
        name = row[1]
        lab = { 'id': id, 'name': name, 'pis': set(), 'certs': [] }
        #labs['data'].append(lab)
        labs['byId'][id] = lab
    return labs


def get_all_certs(cursor):
    """ Get all certs """

    cursor.execute("SELECT * FROM lfs_lab_cert_tracker_cert;")
    rows = cursor.fetchall()
    certs = { 'data': [], 'byId': {} }
    for row in rows:
        id = row[0]
        name = row[1]
        cert = { 'id': id, 'name': name }
        #certs['data'].append(cert)
        certs['byId'][id] = cert
    return certs


def get_all_userlabs(cursor):
    """ Get all userlabs """

    cursor.execute("SELECT * FROM lfs_lab_cert_tracker_userlab;")
    rows = cursor.fetchall()
    return [ { 'id': row[0], 'role': row[1],'lab_id': row[2], 'user_id': row[3] } for row in rows ]


def get_all_labcerts(cursor):
    """ Get all labcerts """
    cursor.execute("SELECT * FROM lfs_lab_cert_tracker_labcert;")
    rows = cursor.fetchall()
    return [ { 'id': row[0], 'cert_id': row[1], 'lab_id': row[2] } for row in rows ]


def get_all_usercerts(cursor):
    """ Get all usercerts """

    cursor.execute("SELECT * FROM lfs_lab_cert_tracker_usercert;")
    rows = cursor.fetchall()
    return [ {
        'id': row[0],
        'expiry_date': change_date_format(row[1]),
        'cert_id': row[2],
        'user_id': row[3],
        'completion_date': change_date_format(row[6])
    } for row in rows ]


def fetch_data(cursor):
    """ Fetch data and make it useful """
    users = get_all_users(cursor)
    labs = get_all_labs(cursor)
    certs = get_all_certs(cursor)
    labcerts = get_all_labcerts(cursor)
    userlabs = get_all_userlabs(cursor)
    usercerts = get_all_usercerts(cursor)
    all_certs = copy.deepcopy(certs)

    for labcert in labcerts:
        lab = labs['byId'][ labcert['lab_id'] ]
        cert = certs['byId'][ labcert['cert_id'] ]
        lab['certs'].append(cert)

    for userlab in userlabs:
        role = userlab['role']
        lab = labs['byId'][ userlab['lab_id'] ]
        user = users['byId'][ userlab['user_id'] ]

        if role == 1:
            lab['pis'].add(userlab['user_id'])

        user['labs'].append(lab)

    for usercert in usercerts:
        cert_id = usercert['cert_id']
        user_id = usercert['user_id']
        expiry_date = usercert['expiry_date']
        completion_date = usercert['completion_date']

    for usercert in usercerts:
        cert_id = usercert['cert_id']
        user_id = usercert['user_id']
        expiry_date = usercert['expiry_date']
        completion_date = usercert['completion_date']

        # Important!
        # Each lab should be updated by user_id for certificates
        labs = copy.deepcopy(users['byId'][user_id]['labs'])

        for lab in labs:
            certs = lab['certs']
            for cert in certs:
                if cert_id == cert['id']:
                    cert['expiry_date'] = expiry_date
                    cert['completion_date'] = completion_date
                    if users['byId'][user_id]['has_expiry_cert'] == False:
                        users['byId'][user_id]['has_expiry_cert'] = expiry_date != completion_date

        users['byId'][user_id]['labs'] = labs

    return users, all_certs


def find_admin(users):
    """ Find administrators """

    admin = set()
    for id, user in users['byId'].items():
        if user['is_superuser'] == True:
            admin.add(user['id'])

    return admin


def find_users_by_days(users, target_day):
    """ Find lab users and PIs who have any certificates to be expired
    in a target day """

    lab_users = []
    pis = {}
    for id, user in users['byId'].items():
        if user['has_expiry_cert'] == True:
            lab_user = { 'id': user['id'], 'certs': set() }

            for lab in user['labs']:
                for pi in lab['pis']:
                    if not pi in pis:
                        pis[pi] = set()

                for cert in lab['certs']:
                    if 'expiry_date' in cert and cert['expiry_date'] == target_day:
                        lab_user['certs'].add(cert['id'])
                        for pi in lab['pis']:
                            pis[pi].add(user['id'])

            if len(lab_user['certs']) > 0:
                lab_users.append(lab_user)

    return lab_users, pis


def find_users(users, type):
    """ Find lab users, Pis, or administators by type """

    if type == 1:
        target_day = datetime.now() + timedelta(days=DAYS30)
        lab_users, pis = find_users_by_days( users, change_date_format(target_day.date()) )
        return lab_users, pis, None

    elif type == 2:
        target_day = datetime.now() + timedelta(days=DAYS14)
        lab_users, pis = find_users_by_days( users, change_date_format(target_day.date()) )
        admin = find_admin(users)
        return lab_users, None, admin

    elif type == 3:
        target_day = datetime.now() - timedelta(days=DAYS14)
        lab_users, pis = find_users_by_days( users, change_date_format(target_day.date()) )
        admin = find_admin(users)
        return lab_users, pis, admin


def get_lab_users_list(users, info):
    """ Get a list of lab users """

    lab_users = []
    for lab_user in info['lab_users']:
        if isinstance(lab_user, int):
            user = users[lab_user]
        else:
            user = users[ lab_user['id'] ]

        lab_users.append("<li>" + user['first_name'] + " " + user['last_name']
            + " (<a href='" + LFS_LAB_CERT_TRACKER_URL
            + "/users/" + str(user['id']) + "/report'>User report</a>)</li>")

    return "".join(lab_users)


def get_lab_users_list_message(days, lab_users_list):
    """ Get a message with a list of lab users """

    message = '''\
        <p>Lab users' certificates will be expired in {0} days.</p>
        <ul>{1}</ul>
    '''.format(days, lab_users_list)

    return message


def get_receiver(users, id):
    """ Get a receiver for an email receiver """

    user_info = users[id]
    return '{0} {1} <{2}>'.format(user_info['first_name'], user_info['last_name'], user_info['email'])


def get_email_info(users, certs, days, role, info):
    """ Get an email infomation such as a receiver and a template by a role """

    user_info = users[ info['id'] ]
    receiver = get_receiver(users, info['id'])

    if role == 'lab_user':
        certificates = []
        for cert_id in info['certs']:
            cert = certs[cert_id]
            certificates.append("<li>" + cert['name'] + "</li>")

        message = '''\
            <p>Your certificate(s) will be expired in {0} days.</p>
            <ul>{1}</ul>
            <p>See <a href="{2}/users/{3}/report">User report</a></p>
        '''.format(days, "".join(certificates), LFS_LAB_CERT_TRACKER_URL, info['id'])

        template = html_template(user_info['first_name'], user_info['last_name'], message)

    elif role == 'pi':
        lab_users_list = get_lab_users_list(users, info)
        message = get_lab_users_list_message(days, lab_users_list)
        template = html_template(user_info['first_name'], user_info['last_name'], message)
    else:
        lab_users_list = get_lab_users_list(users, info)
        message = get_lab_users_list_message(days, lab_users_list)
        template = html_template('Administrators', 'for LFS Cert Tracker', message)

    return receiver, template


def send_email_to_lab_users(users, certs, lab_users, days):
    """ Send an email to lab users"""

    for user in lab_users:
        if len(user['certs']) > 0:
            receiver, message = get_email_info(users['byId'], certs['byId'], days, 'lab_user', user)
            send_email(receiver, message)


def send_email_to_pis(users, certs, pis, days):
    """ Send an email to PIs"""

    for id, lab_users in pis.items():
        if len(lab_users) > 0:
            info = { 'id': id, 'lab_users': lab_users  }
            receiver, message = get_email_info(users['byId'], certs['byId'], days, 'pi', info)
            send_email(receiver, message)


def send_email_to_admin(users, certs, admin, lab_users, days):
    """ Send an email to Administrators """

    for admin_id in admin:
        info = { 'id': admin_id, 'lab_users': lab_users }
        receiver, message = get_email_info(users['byId'], certs['byId'], days, 'admin', info)
        send_email(receiver, message)


def send_email_by_type_one(users, certs):
    """ Send an email to lab users and PIs 1 month before the expiry date """

    lab_users, pis, admin = find_users(users, 1)
    if len(lab_users) > 0:
        send_email_to_lab_users(users, certs, lab_users, DAYS30)
        if len(pis.keys()) > 0:
            send_email_to_pis(users, certs, pis, DAYS30)


def send_email_by_type_two(users, certs):
    """ Send an email to administrators 2 weeks before the expiry date """

    lab_users, pis, admin = find_users(users, 2)
    if len(lab_users) > 0 and len(admin) > 0:
        send_email_to_admin(users, certs, admin, DAYS14)


def send_email_by_type_three(users, certs):
    """ Send an email to all of them 2 weeks after the expiry date """

    lab_users, pis, admin = find_users(users, 3)
    if len(lab_users) > 0:
        send_email_to_lab_users(users, certs, lab_users, DAYS14)

        if len(pis.keys()) > 0:
            send_email_to_pis(users, certs, pis, DAYS14)

        if len(admin) > 0:
            send_email_to_admin(users, certs, admin, lab_users, DAYS14)


def html_template(first_name, last_name, message):
    """ Get a base of html template"""
    template = '''\
    <html>
      <head></head>
      <body>
        <p>Hi {0} {1},</p>
        <div>{2}</div>
        <p>Best regards,</p>
        <p>LFS Cert Tracker</p>
      </body>
    </html>
    '''.format(first_name, last_name, message)

    return template


def send_email(receiver, message):
    """Send an email with a receiver and a message """

    smtp_server = os.environ['LFS_LAB_CERT_TRACKER_EMAIL_HOST']
    password = None
    port = None

    sender = os.environ['LFS_LAB_CERT_TRACKER_EMAIL_FROM']
    msg = MIMEText(message, 'html')
    msg['Subject'] = 'Certificate Notification'
    msg['From'] = sender
    msg['To'] = receiver

    try:
    	server = smtplib.SMTP(smtp_server)
    	#server.ehlo()
    	#server.starttls(context=ssl.create_default_context())
    	#server.ehlo()
    	#server.login(sender_email, password)
    	server.sendmail(sender, receiver, msg.as_string())
    except Exception as e:
    	print(e)
    finally:
    	server.quit()


# Set up and connect to a database
USER = os.environ['LFS_LAB_CERT_TRACKER_DB_USER']
PASSWORD = os.environ['LFS_LAB_CERT_TRACKER_DB_PASSWORD']
HOST = os.environ['LFS_LAB_CERT_TRACKER_DB_HOST']
PORT = os.environ['LFS_LAB_CERT_TRACKER_DB_PORT']
DATABASE = os.environ['LFS_LAB_CERT_TRACKER_DB_NAME']

try:
    connection = psycopg2.connect(user=USER, password=PASSWORD, host=HOST, port=PORT, database=DATABASE)
    cursor = connection.cursor()

except (Exception, psycopg2.Error) as error :
    print ("Error while connecting to PostgreSQL", error)
finally:
    if connection:

        # Fetch data
        users, certs = fetch_data(cursor)

        # Send emails for student/PI (1 month prior to expiry date)
        send_email_by_type_one(users, certs)

        # Send emails for admin (2 weeks before the expiry date)
        send_email_by_type_two(users, certs)

        # Send emails to student/PI/admin (2 weeks after the expiry date)
        send_email_by_type_three(users, certs)

        cursor.close()
        connection.close()
