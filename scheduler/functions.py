from django.conf import settings
from django.db.models import Q, F, Max
import os
import smtplib
import requests
from datetime import date
from email.mime.text import MIMEText

from django.contrib.auth.models import User
from lfs_lab_cert_tracker.models  import Cert, UserLab, UserCert, LabCert

from app import functions as appFunc


def get_next_url(curr_page):
    return '{0}?page={1}&pageSize={2}'.format(settings.LFS_LAB_CERT_TRACKER_API_URL, curr_page, 50)


def get_expiry_date(completion_date, cert):
    expiry_year = completion_date.year + int(cert.expiry_in_years)
    return date(year=expiry_year, month=completion_date.month, day=completion_date.day)


def pull_by_api(headers, certs, usernames, validation):
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
            if 'requestedIdentifier' not in item.keys() or 'certificate' not in item.keys() or 'identifier' not in item['requestedIdentifier'].keys() or 'trainingName' not in item['certificate'].keys() or 'trainingId' not in item['certificate'].keys() or 'completionDate' not in item['certificate'].keys():
                print('Warning: no requestedIdentifier, certificate, identifier, trainingName or completionDate')
                continue

            username = item['requestedIdentifier']['identifier']
            training_name = item['certificate']['trainingName'].strip()
            training_id = item['certificate']['trainingId']
            completion_date = item['certificate']['completionDate'].split('T')[0].split('-')

            if item['certificate']['status'] == 'active' and len(completion_date) == 3:
                completion_date = date(year=int(completion_date[0]), month=int(completion_date[1]), day=int(completion_date[2]))
                user = appFunc.get_user_by_username(username)
                
                cert = find_cert_by_unique_id(certs, training_id)
                #cert = find_cert(certs, training_name)
                
                if user and cert:
                    user_certs = user.usercert_set.filter(cert_id=cert.id, completion_date=completion_date)
                    form = '{0}_{1}_{2}'.format(user.id, cert.id, completion_date)

                    if not user_certs.exists() and form not in validation:
                        validation.append(form)                        
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
                print('Warning: completion date is wrong, or status is not active:', username, training_name)
        
        hasNextPage = json['hasNextPage']
        next_url = get_next_url(int(json['page']) + 1)
    
    return data, validation


def find_cert_by_unique_id(certs, unique_id):
    training = None
    
    cert_obj = Cert.objects.filter(unique_id__icontains=unique_id)
    if cert_obj.exists():
        for cert in cert_obj:
            ids = cert.unique_id.split('/')
            if str(unique_id) in ids:
                training = cert
                break

    return training


def find_cert(certs, training_name):
    if training_name == 'Chemical Safety' or training_name == 'Chemical Safety Refresher':
        training_name = 'Chemical Safety/Chemical Safety Refresher'
    elif training_name == 'Biosafety for Study Team Members' or training_name == 'Biosafety Refresher for Study Team Members':
        training_name = 'Biosafety for Study Team Members/Biosafety Refresher for Study Team Members'
    elif training_name == 'Biosafety for Permit Holders' or training_name == 'Biosafety Refresher for Permit Holders':
        training_name = 'Biosafety for Permit Holders/Biosafety Refresher for Permit Holders'
    elif training_name == 'Transportation of Dangerous Goods by Ground and Air_ April 2020- March 7 2022':
        training_name = 'Transportation of Dangerous Goods by Ground and Air'
    elif training_name == "Remote Work. Home Office Ergonomics. Orientation":
        training_name = "Home Office Ergo"

    cert = Cert.objects.filter(name=training_name)    
    return cert.first() if cert.exists() else None


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
    for user in appFunc.get_users('active'):
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


def find_expired_trainings(active_users, target_day, type):
    """ Find expired trainings of each user on the target day """

    lab_users = []
    pis = {}

    for user in active_users:
        if user.usercert_set.count() > 0:
            lab_user = { 'id': user.id, 'trainings': [] }
            
            user_certs = []
            if type == 'before':
                user_certs_with_max_expiry_date = user.usercert_set.values('cert_id').annotate(max_expiry_date=Max('expiry_date')).filter( Q(max_expiry_date=target_day) & ~Q(completion_date=F('expiry_date')) )
            elif type == 'after':
                user_certs_with_max_expiry_date = user.usercert_set.values('cert_id').annotate(max_expiry_date=Max('expiry_date')).filter( Q(max_expiry_date__lt=target_day) & ~Q(completion_date=F('expiry_date')) )
            
            for uc in user_certs_with_max_expiry_date:
                user_cert = UserCert.objects.filter(user_id=user.id, cert_id=uc['cert_id'], expiry_date=uc['max_expiry_date'])
                user_certs.append(user_cert.first())
            
            for user_cert in user_certs:
                lab_user, pis = help_find_expired_trainings(user, user_cert, lab_user, pis)
            
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
                    if pi not in pis.keys(): 
                        pis[pi] = dict()
                    
                    if user.id not in pis[pi]: 
                        pis[pi][user.id] = []
                    
                    ids = [item['id'] for item in pis[pi][user.id]]
                    if info['id'] not in ids:
                        pis[pi][user.id].append(info)

    return lab_user, pis


# Methods to send emails

def send_email(receiver, message):
    """ Send an email with a receiver and a message """
    
    if settings.EMAIL_FROM:
        sender = settings.EMAIL_FROM

        msg = MIMEText(message, 'html')
        msg['Subject'] = 'Training Record Notification'
        msg['From'] = sender
        msg['To'] = receiver

        try:
            server = smtplib.SMTP(settings.EMAIL_HOST)
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


def get_receiver(first_name, last_name, email):
    """ Get a receiver for an email receiver """
    return '{0} {1} <{2}>'.format(first_name, last_name, email)


def datetime_to_string(datetime):
    """ Convert datetime to string """
    return datetime.strftime('%m/%d/%Y')


# For missing trainings
def get_message_users_missing_trainings(user_id, trainings):
    """ Get a message for lab users """

    contents = []
    for area in trainings.keys():
        area_split = area.split('|')
        area_id = area_split[0]
        area_name = area_split[1]
        trainings = trainings[area]

        content = '<p>{0}</p><ul>'.format(area_name)
        for training in trainings:
            content += '<li>{0}</li>'.format(training)
        content += '</ul>'

        contents.append(content)

    message = """\
<p>Our records indicate that you have missing training certification(s) required for each area. Please take a moment to update your records at your earliest convenience. Let us know if you need any assistance.</p>
<div>{0}</div>
<p>See <a href="{1}/app/users/{2}/report.pdf/">User report</a></p>
    """.format(''.join(contents), settings.SITE_URL, user_id)

    return message


def get_message_pis_missing_trainings(contents):
    """ Get a message for PIs """

    message = """\
<p>Please be advised that the following users have missing required training certification(s) for your area. Kindly review the list and ensure appropriate actions are taken.</p>
<div>{0}</div>
<p>Let us know if you need any further details or assistance.</p>
    """.format(contents)

    return message


# For expiry trainings
def get_message_users_expired_trainings(user_id, trainings, days, type):
    """ Get a message with a list of users for lab users """

    contents = []
    for tr in trainings:
        content = '<li>{0} (Expiry Date: {1})</li>'.format(tr['name'], tr['expiry_date'])
        contents.append(content)

    if type == 'before':
        message = """\
<p>Your training(s) will expire in {0} days.</p>
<ul>{1}</ul>
<p>See <a href='{2}/app/users/{3}/report.pdf/'>User Report</a></p>
        """.format(days, ''.join(contents), settings.SITE_URL, user_id)
    else:
        message = """\
<p>Your training expiration date has already passed. Please update it.</p>
<ul>{0}</ul>
<p>See <a href='{1}/app/users/{2}/report.pdf/'>User Report</a></p>
        """.format(''.join(contents), settings.SITE_URL, user_id)

    return message


def get_message_pis_expired_trainings(contents, days, type):
    """ Get a message with a list of users """

    if type == 'before':
        message = """\
<p>Trainings of the following users in your area will expire in {0} days.</p>
{1}
        """.format(days, contents)
    else:
        message = """\
<p>The following users have expired training(s).</p>
{0}
        """.format(contents)

    return message


def send_email_to_lab_users(lab_users, days, type):
    """ Send an email to lab users """

    for lab_user in lab_users:
        user_id = lab_user['id']

        if len(lab_user['trainings']) > 0:
            user = appFunc.get_user_by_id(user_id)

            trainings = []
            for item in lab_user['trainings']:
                trainings.append('<li>' + item['training'].name + ' (Expiry Date: ' + datetime_to_string(item['expiry_date']) + ')</li>')

            receiver = get_receiver(user)
            message = get_message_users_expired_trainings(trainings, user_id, days, type)
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
                    pi = appFunc.get_user_by_id(pid)
                    user = appFunc.get_user_by_id(user_id)

                    content = '<div>' + user.first_name + ' ' + user.last_name + '</div><ul>'
                    for item in trainings:
                        content += '<li>' + item['training'].name + ' (Expiry Date: ' + datetime_to_string(item['expiry_date']) + ')</li>'
                    content += '</ul><br />'
                    contents.append(content)

            if len(contents) > 0:
                lab_users_list =  ''.join(contents)

                pi = appFunc.get_user_by_id(pid)
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
        user = appFunc.get_user_by_id(user_id)
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
