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
        <br />
        <div>
            <b>Please note that if you try to access the LFS Training Record Management System off campus,
            you must be connected via
            <a href="https://it.ubc.ca/services/email-voice-internet/myvpn">UBC VPN</a>.</b>
        </div>
        <br /><br />
        <div>
            If you are trying to enroll in a missing or expired training, or to retrieve the training completion record, please visit the following links to get to the appropriate sites:
            <p>
                <b>UBC/LFS Mandatory Training</b><br />
                <a href="https://my.landfood.ubc.ca/lfs-mandatory-training">https://my.landfood.ubc.ca/lfs-mandatory-training</a>
            </p>
        </div>
        <br />
        <p>Best regards,</p>
        <p>LFS Training Record Management System</p>
      </body>
    </html>
    '''.format(first_name, last_name, message)

    return template


def get_message_lab_users(certificates, user, days, type):
    """ Get a message with a list of users for lab users"""

    if type == 'before':
        message = '''\
            <p>Your training(s) will expire in {0} days.</p>
            <ul>{1}</ul>
            <p>See <a href="{2}/users/{3}/report">User report</a></p>
            '''.format(days, "".join(certificates), LFS_LAB_CERT_TRACKER_URL, user['id'])
    else:
        message = '''\
            <p>Your training expiration date has already passed. Please update it.</p>
            <ul>{0}</ul>
            <p>See <a href="{1}/users/{2}/report">User report</a></p>
            '''.format("".join(certificates), LFS_LAB_CERT_TRACKER_URL, user['id'])

    return message


def get_message(days, lab_users_list, type):
    """ Get a message with a list of users """

    if type == 'before':
        message = '''\
            <p>Trainings of the following users in your area will expire in {0} days.</p>
            {1}
        '''.format(days, lab_users_list)
    else:
        message = '''\
            <p>The following users have expired training(s).</p>
            <ul>{0}</ul>
        '''.format(lab_users_list)

    return message


def send_email_to_lab_users(users, lab_users, days, type):
    """ Send an email to lab users"""

    for lab_user in lab_users:
        if len(lab_user['certs']) > 0:
            certificates = []
            for cert in lab_user['certs']:
                certificates.append("<li>" + cert['name'] + " (Expiry Date: " + datetime_to_string(cert['expiry_date']) + ")</li>")

            user = users[ lab_user['id'] ]

            receiver = get_receiver(user)
            message = get_message_lab_users(certificates, user, days, type)
            template = html_template(user['first_name'], user['last_name'], message)

            send_email(receiver, template)
            print( "User: Sent it to {0}".format(receiver) )


def send_email_to_pis(users, pis, days, type):
    """ Send an email to PIs"""

    for pid, lab_users in pis.items():
        if len(lab_users) > 0:
            contents = []
            for uid, certs in lab_users.items():

                if len(certs) > 0:
                    pi = users[pid]
                    user = users[uid]
                    content = "<div>" + user['first_name'] + " " + user['last_name'] + "</div><ul>"
                    for cert in certs:
                        content += "<li>" + cert['name'] + " (Expiry Date: " + datetime_to_string(cert['expiry_date']) + ")</li>"
                    content += "</ul><br />"
                    contents.append(content)

            if len(contents) > 0:
                lab_users_list =  "".join(contents)

                pi = users[pid]
                receiver = get_receiver(pi)
                message = get_message(days, lab_users_list, type)
                template = html_template(pi['first_name'], pi['last_name'], message)

                send_email(receiver, template)
                print( "Supervisor: Sent it to {0}".format(receiver) )


def send_email_to_admin(users, admin, lab_users, days, type):
    """ Send an email to Administrators """

    contents = []
    for lab_user in lab_users:
        user = users[ lab_user['id'] ]
        content = "<div>" + user['first_name'] + " " + user['last_name'] + " (<a href='" + LFS_LAB_CERT_TRACKER_URL + "/users/" + str(user['id']) + "/report'>User report</a>)</div><ul>"

        for cert in lab_user['certs']:
            content += "<li>" + cert['name'] + " (Expiry Date: " + datetime_to_string(cert['expiry_date']) + ")</li>"
        content += "</ul>"
        contents.append(content)

    lab_users_list =  "".join(contents)

    for admin_id in admin:
        admin = users[admin_id]

        receiver = get_receiver(admin)
        message = get_message(days, lab_users_list, type)
        template = html_template('LFS TRMS', 'administrators', message)

        send_email(receiver, template)
        print( "Admin: Sent it to {0}".format(receiver) )


# Helper functions

def get_receiver(user):
    """ Get a receiver for an email receiver """

    return '{0} {1} <{2}>'.format(user['first_name'], user['last_name'], user['email'])

def datetime_to_string(d):
    """ Convert datetime to string """

    return d.strftime("%m/%d/%Y")
