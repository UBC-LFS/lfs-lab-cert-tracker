from django.conf import settings
from datetime import date
import smtplib
from email.mime.text import MIMEText
import re
import requests

from django.contrib.auth.models import User
from lfs_lab_cert_tracker.models  import UserCert, LabCert

from app.functions import *


def get_admins():
    """ Get all administrators """
    return User.objects.filter(is_superuser=True)

def get_next_url(curr_page):
    return '{0}?page={1}&pageSize={2}'.format(settings.LFS_LAB_CERT_TRACKER_API_URL, curr_page, 50)


def pull_by_api(headers, certs, usernames):
    data = []
    
    body = { 'requestIdentifiers': [{ 'identifierType': 'CWL', 'identifier': username } for username in usernames] }
    next_url = get_next_url(1)
    hasNextPage = True

    while hasNextPage:
        res = requests.post(next_url, json=body, headers=headers)
        if res.status_code != 200:
            print('Error occurred:', res.status_code)
            break

        json = res.json()
        if 'page' not in json.keys() or 'pageSize' not in json.keys() or 'hasNextPage' not in json.keys() or 'pageItems' not in json.keys():
            print('Error: page, pageSize, hasNextPage and pageItems are required.')
            break
        
        for item in json['pageItems']:
            if 'requestedIdentifier' not in item.keys() or 'certificate' not in item.keys() or 'identifier' not in item['requestedIdentifier'].keys() or 'trainingName' not in item['certificate'].keys() or 'completionDate' not in item['certificate'].keys():
                print('Warning: no requestedIdentifier, certificate, identifier, trainingName or completionDate')
                continue

            username = item['requestedIdentifier']['identifier']
            training_name = item['certificate']['trainingName']
            completion_date = item['certificate']['completionDate'].split('T')[0].split('-')

            if len(completion_date) == 3:
                completion_date = date(year=int(completion_date[0]), month=int(completion_date[1]), day=int(completion_date[2]))
                user = get_user_by_username(username)
                cert = find_cert(certs, training_name)
                if user and cert:
                    user_certs = user.usercert_set.filter(cert_id=cert.id, completion_date=completion_date)
                    if not user_certs.exists():
                        data.append(UserCert(
                            user = user,
                            cert = cert,
                            cert_file = 'None',
                            uploaded_date = date.today(),
                            completion_date = completion_date,
                            expiry_date = get_expiry_date(completion_date, cert),
                            by_api = True
                        ))
            else:
                print('Warning: len(competion date) == 3', username, training_name)
        
        hasNextPage = json['hasNextPage']
        next_url = get_next_url(int(json['page']) + 1)
    
    return data


def remove_special_chars(s):
    return re.findall(r'\b(?:[A-Za-z]\w*|\d+)\b', s.strip().lower())

def find_cert(certs, training_name):
    training_name = training_name.replace('Online', '')
    training_name = training_name.replace('Self Paced', '')
    training_name = training_name.replace('no longer required', '')
    
    d1 = {}
    l1 = remove_special_chars(training_name)
    for word in l1:
        if word in ['and','for','of','in','or','to','by']:
            continue
        if word in d1.keys(): d1[word] += 1
        else: d1[word] = 1
    
    best = None
    max_count = 0
    for cert in certs:
        d2 = {}
        l2 = remove_special_chars(cert.name)
        for word in l2:
            if word in ['and','for','of','in','or','to','by']:
                continue
            if word in d2.keys(): d2[word] += 1
            else: d2[word] = 1   
        
        count = 0
        for k, v in d1.items():
            if k in d2.keys() and d2[k] == v:
                count += 1
        if count > max_count:
            best = cert
            max_count = count
        
    return best if max_count / len(d1.keys()) > 0.70 else None


# Email Notification

def get_areas_in_user():
    """ Get areas in user """

    areas_in_user = {}
    for userlab in UserLab.objects.all():
        if userlab.user.is_active:
            if userlab.user.id not in areas_in_user:
                areas_in_user[ userlab.user.id ] = set()

            areas_in_user[ userlab.user.id ].add(userlab.lab.id)

    return areas_in_user

def get_trainings_in_user():
    """ Get trainings in each user """

    trainings_in_user = {}
    for usercert in UserCert.objects.all():
        if usercert.user.is_active:
            if usercert.user.id not in trainings_in_user:
                trainings_in_user[ usercert.user.id ] = set()

            trainings_in_user[ usercert.user.id ].add(usercert.cert.id)

    return trainings_in_user


def get_infomation_in_area():
    """ Get PIs and required trainings in each area """

    pis_in_area = {}
    required_trainings_in_area = {}

    # Get PIs in each area
    for userlab in UserLab.objects.all():
        if userlab.user.is_active:
            if userlab.role == UserLab.PRINCIPAL_INVESTIGATOR:
                if userlab.lab.id not in pis_in_area.keys():
                    pis_in_area[ userlab.lab.id ] = set()

                pis_in_area[ userlab.lab.id ].add(userlab.user.id)

    # Get required trainings in each area
    for labcert in LabCert.objects.all():
        if labcert.lab.id not in required_trainings_in_area.keys():
            required_trainings_in_area[ labcert.lab.id ] = set()

        required_trainings_in_area[ labcert.lab.id ].add(labcert.cert.id)

    return pis_in_area, required_trainings_in_area


def find_missing_trainings():
    """ Find missing trainings of each user """

    lab_users = []
    pis = {}

    pis_in_area, required_trainings_in_area = get_infomation_in_area()

    # Create a set of PIs
    for area_id, supervisors in pis_in_area.items():
        for supervisor in supervisors:
            if supervisor not in pis.keys():
                pis[supervisor] = set()

    # Insert users when missing trainings exist
    for user in get_users('active'):
        if user.userlab_set.count() > 0:
            missing_trainings = set()

            for userlab in user.userlab_set.all():
                temp_missing_trainings = set()
                if userlab.lab.id in required_trainings_in_area.keys():
                    if userlab.user.id in get_trainings_in_user().keys():
                        temp_missing_trainings = required_trainings_in_area[ userlab.lab.id ] - get_trainings_in_user()[ userlab.user.id ]
                    else:
                        temp_missing_trainings = required_trainings_in_area[ userlab.lab.id ]

                # If there are some missing trainings found, then add PIs in thi work area
                if len(temp_missing_trainings) > 0:
                    if userlab.lab.id in pis_in_area:
                        for sup in pis_in_area[ userlab.lab.id ]:
                            pis[sup].add(user.id)

                # Update some of missing trainings to a set of missing trainings
                missing_trainings.update(temp_missing_trainings)

            if len(missing_trainings) > 0:
                lab_users.append({ 'id': user.id, 'user': user, 'missing_trainings': list(missing_trainings) })

    return lab_users, pis


def find_expired_trainings(target_day, type):
    """ Find expired trainings of each user on the target day """

    lab_users = []
    pis = {}

    for user in get_users('active'):
        if user.usercert_set.count() > 0:
            lab_user = { 'id': user.id, 'trainings': [] }

            for usercert in user.usercert_set.all():
                if usercert.completion_date != usercert.expiry_date:

                    if type == 'before':
                        if usercert.expiry_date == target_day:
                            lab_user, pis = help_find_expired_trainings(user, usercert, lab_user, pis)

                    elif type == 'after':
                        if usercert.expiry_date < target_day:
                            lab_user, pis = help_find_expired_trainings(user, usercert, lab_user, pis)

            if len(lab_user['trainings']) > 0:
                lab_users.append(lab_user)

    return lab_users, pis


def help_find_expired_trainings(user, usercert, lab_user, pis):
    """ Help to find expired trainings  """

    pis_in_area, required_trainings_in_area = get_infomation_in_area()

    for userlab in user.userlab_set.all():
        if usercert.cert.id in required_trainings_in_area[ userlab.lab.id ]:
            info = {
                'id': usercert.cert.id,
                'training': usercert.cert,
                'completion_date': usercert.completion_date,
                'expiry_date': usercert.expiry_date
            }

            # Check if training contains or not in the list of trainings of a lab user
            if usercert.cert.id not in [ training['id'] for training in lab_user['trainings'] ]:
                lab_user['trainings'].append(info)

            # Insert PIs in this work area
            if userlab.lab.id in pis_in_area.keys():
                for pi in pis_in_area[ userlab.lab.id ]:
                    if pi not in pis.keys(): pis[pi] = dict()
                    if user.id not in pis[pi]: pis[pi][user.id] = []

                    pis[pi][user.id].append(info)

    return lab_user, pis


# Methods to send emails

def send_email(receiver, message):
    """ Send an email with a receiver and a message """

    sender = os.environ['LFS_LAB_CERT_TRACKER_EMAIL_FROM']
    msg = MIMEText(message, 'html')
    msg['Subject'] = 'Training Record Notification'
    msg['From'] = sender
    msg['To'] = receiver

    try:
        server = smtplib.SMTP(os.environ['LFS_LAB_CERT_TRACKER_EMAIL_HOST'])
        server.sendmail(sender, receiver, msg.as_string())
    except Exception as e:
        print(e)
    finally:
        server.quit()


def html_template(first_name, last_name, message):
    """ Get a base of html template """

    template = """\
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
    """.format(first_name, last_name, message)

    return template


def get_receiver(user):
    """ Get a receiver for an email receiver """

    return '{0} {1} <{2}>'.format(user.first_name, user.last_name, user.email)

def datetime_to_string(datetime):
    """ Convert datetime to string """

    return datetime.strftime('%m/%d/%Y')


# For missing trainings
def get_message_lab_users_missing_trainings(user_id, missing_trainings):
    """ Get a message for lab users """

    trainings = []
    for training_id in missing_trainings:
        trainings.append('<li>' + get_cert_by_id(training_id).name + '</li>')

    message = """\
        <p>You have missing training(s). Please update it.</p>
        <ul>{0}</ul>
        <p>See <a href="{1}/app/users/{2}/report.pdf/">User report</a></p>
    """.format(''.join(trainings), settings.SITE_URL, user_id)

    return message


def get_message_pis_missing_trainings(lab_users):
    """ Get a message for PIs """

    lab_users_list = []
    for uid in lab_users:
        lab_users_list.append('<li>' + get_user_by_id(uid).first_name + ' ' + get_user_by_id(uid).last_name + '</li>')

    message = """\
        <p>The following users have missing training(s).</p>
        <ul>{0}</ul>
    """.format( ''.join(lab_users_list) )

    return message


# For expiry trainings
def get_message_lab_users_expired_trainings(trainings, user_id, days, type):
    """ Get a message with a list of users for lab users """

    if type == 'before':
        message = """\
            <p>Your training(s) will expire in {0} days.</p>
            <ul>{1}</ul>
            <p>See <a href="{2}/app/users/{3}/report.pdf/">User report</a></p>
            """.format(days, "".join(trainings), settings.SITE_URL, user_id)
    else:
        message = """\
            <p>Your training expiration date has already passed. Please update it.</p>
            <ul>{0}</ul>
            <p>See <a href="{1}/app/users/{2}/report.pdf/">User report</a></p>
            """.format("".join(trainings), settings.SITE_URL, user_id)

    return message


def get_message_pis_expired_trainings(lab_users_list, days, type):
    """ Get a message with a list of users """

    if type == 'before':
        message = """\
            <p>Trainings of the following users in your area will expire in {0} days.</p>
            {1}
        """.format(days, lab_users_list)
    else:
        message = """\
            <p>The following users have expired training(s).</p>
            <ul>{0}</ul>
        """.format(lab_users_list)

    return message


def send_email_to_lab_users(lab_users, days, type):
    """ Send an email to lab users """

    for lab_user in lab_users:
        user_id = lab_user['id']

        if len(lab_user['trainings']) > 0:
            user = get_user_by_id(user_id)

            trainings = []
            for item in lab_user['trainings']:
                trainings.append('<li>' + item['training'].name + ' (Expiry Date: ' + datetime_to_string(item['expiry_date']) + ')</li>')

            receiver = get_receiver(user)
            message = get_message_lab_users_expired_trainings(trainings, user_id, days, type)
            template = html_template(user.first_name, user.last_name, message)

            send_email(receiver, template)
            print( 'User: Sent it to {0}'.format(receiver) )


def send_email_to_pis(pis, days, type):
    """ Send an email to PIs """

    for pid, lab_users in pis.items():

        if len(lab_users) > 0:
            contents = []
            for user_id, trainings in lab_users.items():

                if len(trainings) > 0:
                    pi = get_user_by_id(pid)
                    user = get_user_by_id(user_id)

                    content = '<div>' + user.first_name + ' ' + user.last_name + '</div><ul>'
                    for item in trainings:
                        content += '<li>' + item['training'].name + ' (Expiry Date: ' + datetime_to_string(item['expiry_date']) + ')</li>'
                    content += '</ul><br />'
                    contents.append(content)

            if len(contents) > 0:
                lab_users_list =  ''.join(contents)

                pi = get_user_by_id(pid)
                receiver = get_receiver(pi)
                message = get_message_pis_expired_trainings(lab_users_list, days, type)
                template = html_template(pi.first_name, pi.last_name, message)

                send_email(receiver, template)
                print( "Supervisor: Sent it to {0}".format(receiver) )

def send_email_to_admins(admins, lab_users, days, type):
    """ Send an email to admins """

    contents = []
    for lab_user in lab_users:
        user_id = lab_user['id']
        user = get_user_by_id(user_id)
        content = '<div>' + user.first_name + ' ' + user.last_name + " (<a href='" + settings.SITE_URL + '/app/users/' + str(user_id) + "/report.pdf/'>User report</a>)</div><ul>"

        for item in lab_user['trainings']:
            content += '<li>' + item['training'].name + ' (Expiry Date: ' + datetime_to_string(item['expiry_date']) + ')</li>'

        content += '</ul>'
        contents.append(content)

    lab_users_list = ''.join(contents)

    for admin in admins:
        receiver = get_receiver(admin)
        message = get_message_pis_expired_trainings(lab_users_list, days, type)
        template = html_template('LFS TRMS', 'administrators', message)

        send_email(receiver, template)
        print( 'Admin: Sent it to {0}'.format(receiver) )
