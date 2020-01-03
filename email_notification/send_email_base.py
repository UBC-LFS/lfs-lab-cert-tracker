import smtplib, ssl
from email.mime.text import MIMEText
from send_email_settings import *


def send_email(receiver, message):
    """Send an email with a receiver and a message """

    password = None
    port = None

    sender = SENDER
    msg = MIMEText(message, 'html')
    msg['Subject'] = 'Training Record Notification'
    msg['From'] = sender
    msg['To'] = receiver

    try:
    	server = smtplib.SMTP(SMTP_SERVER)
    	#server.ehlo()
    	#server.starttls(context=ssl.create_default_context())
    	#server.ehlo()
    	#server.login(sender_email, password)
    	server.sendmail(sender, receiver, msg.as_string())
    except Exception as e:
    	print(e)
    finally:
    	server.quit()


def html_template(first_name, last_name, message):
    """ Get a base of html template"""
    template = '''\
    <html>
      <head></head>
      <body>
        <p>Hi {0} {1},</p>
        <div>{2}</div>
        <p>Best regards,</p>
        <p>LFS Training Record Management System</p>
      </body>
    </html>
    '''.format(first_name, last_name, message)

    return template


def get_lab_users_list(users, info, role):
    """ Get a list of lab users """

    lab_users = []
    for lab_user in info['lab_users']:
        if isinstance(lab_user, int):
            user = users[lab_user]
        else:
            user = users[ lab_user['id'] ]

        if role == 'pi':
            lab_users.append("<li>" + user['first_name'] + " " + user['last_name'] + "</li>")
        else:
            lab_users.append("<li>" + user['first_name'] + " " + user['last_name']
                + " (<a href='" + LFS_LAB_CERT_TRACKER_URL
                + "/users/" + str(user['id']) + "/report'>User report</a>)</li>")

    return "".join(lab_users)


def get_message_lab_users(certificates, info, days, type):
    """ Get a message with a list of users for lab users"""

    if type == 'before':
        message = '''\
            <p>Your training(s) will expire in {0} days.</p>
            <ul>{1}</ul>
            <p>See <a href="{2}/users/{3}/report">User report</a></p>
            '''.format(days, "".join(certificates), LFS_LAB_CERT_TRACKER_URL, info['id'])
    else:
        message = '''\
            <p>Your training expiration date has already passed. Please update it.</p>
            <ul>{0}</ul>
            <p>See <a href="{1}/users/{2}/report">User report</a></p>
            '''.format("".join(certificates), LFS_LAB_CERT_TRACKER_URL, info['id'])

    return message


def get_message(days, lab_users_list, type):
    """ Get a message with a list of users """

    if type == 'before':
        message = '''\
            <p>Trainings of the following users in your area will expire in {0} days.</p>
            <ul>{1}</ul>
        '''.format(days, lab_users_list)
    else:
        message = '''\
            <p>The following users have expired training(s).</p>
            <ul>{0}</ul>
        '''.format(lab_users_list)

    return message


def get_receiver(users, id):
    """ Get a receiver for an email receiver """

    user_info = users[id]
    return '{0} {1} <{2}>'.format(user_info['first_name'], user_info['last_name'], user_info['email'])


def get_email_info(users, certs, days, role, info, type):
    """ Get an email infomation such as a receiver and a template by a role """

    user_info = users[ info['id'] ]
    receiver = get_receiver(users, info['id'])

    if role == 'lab_user':
        certificates = []
        for cert_id in info['certs']:
            cert = certs[cert_id]
            certificates.append("<li>" + cert['name'] + "</li>")

        message = get_message_lab_users(certificates, info, days, type)
        template = html_template(user_info['first_name'], user_info['last_name'], message)

    elif role == 'pi':
        lab_users_list = get_lab_users_list(users, info, 'pi')
        message = get_message(days, lab_users_list, type)
        template = html_template(user_info['first_name'], user_info['last_name'], message)

    else:
        lab_users_list = get_lab_users_list(users, info, 'admin')
        message = get_message(days, lab_users_list, type)
        template = html_template('Administrators', 'in LFS Training Record Management System', message)

    return receiver, template


def send_email_to_lab_users(users, certs, lab_users, days, type):
    """ Send an email to lab users"""

    for user in lab_users:
        if len(user['certs']) > 0:
            receiver, message = get_email_info(users, certs, days, 'lab_user', user, type)
            send_email(receiver, message)
            print( "User: Sent it to {0}".format(receiver) )


def send_email_to_pis(users, certs, pis, days, type):
    """ Send an email to PIs"""

    for id, lab_users in pis.items():
        if len(lab_users) > 0:
            info = { 'id': id, 'lab_users': lab_users  }
            receiver, message = get_email_info(users, certs, days, 'pi', info, type)
            send_email(receiver, message)
            print( "Supervisor: Sent it to {0}".format(receiver) )


def send_email_to_admin(users, certs, admin, lab_users, days, type):
    """ Send an email to Administrators """

    for admin_id in admin:
        info = { 'id': admin_id, 'lab_users': lab_users }
        receiver, message = get_email_info(users, certs, days, 'admin', info, type)
        send_email(receiver, message)
        print( "Admin: Sent it to {0}".format(receiver) )
