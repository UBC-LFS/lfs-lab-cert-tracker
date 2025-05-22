from django.conf import settings
from django.db.models import Q, F, Max
from email.mime.text import MIMEText
import smtplib
import requests
from datetime import date

from lfs_lab_cert_tracker.models import Cert, UserCert, LabCert
from django.db.models import Q, F, Max, OuterRef, Exists

from app import functions as appFunc


# Missing trainings

def get_users_missing_trainings():
    ''' Get users' missing trainings '''

    has_cert_subquery = UserCert.objects.filter(user=OuterRef('user'), cert=OuterRef('cert'))
    area_trainings = LabCert.objects.filter(lab__userlab__user__isnull=False).annotate(
        user=F('lab__userlab__user'),
        first_name=F('lab__userlab__user__first_name'),
        last_name=F('lab__userlab__user__last_name'),
        email=F('lab__userlab__user__email'),
        is_active=F('lab__userlab__user__is_active')
    ).filter(
        Q(is_active=False) & 
        Q(~Exists(has_cert_subquery))
    ).values(
        'user', 
        'lab',
        'cert', 
        'lab__name', 
        'cert__name',
        'first_name',
        'last_name',
        'email'
    ).distinct()

    users = {}
    areas = {}
    if area_trainings.exists():
        for at in area_trainings.iterator():
            user_id = str(at['user'])
            area_id = str(at['lab'])

            if user_id not in users.keys():
                users[user_id] = {
                    'first_name': at['first_name'],
                    'last_name': at['last_name'],
                    'email': at['email'],
                    'areas': {}
                }
            
            if area_id not in users[user_id]['areas'].keys():
                users[user_id]['areas'][area_id] = {
                    'name': at['lab__name'],
                    'missing_trainings': []
                }
            
            users[user_id]['areas'][area_id]['missing_trainings'].append(at['cert__name'])

            if area_id not in areas.keys():
                areas[area_id] = {}

            if user_id not in areas[area_id].keys():
                areas[area_id][user_id] = {
                    'full_name': '{0} {1}'.format(at['first_name'], at['last_name']),
                    'missing_trainings': []
                }

            areas[area_id][user_id]['missing_trainings'].append(at['cert__name'])
    
    return users, areas


def get_message_users_missing_trainings(user_id, areas):
    """ Get a message for lab users """

    contents = []
    for area_id in areas.keys():
        area = areas[area_id]

        content = '<p>{0}</p><ul>'.format(area['name'])
        for tr_name in area['missing_trainings']:
            content += '<li>{0}</li>'.format(tr_name)
        content += '</ul>'

        contents.append(content)

    message = """\
        <p>Our records indicate that you have missing training certification(s) required for each area. Please take a moment to update your records at your earliest convenience. Let us know if you need any assistance.</p>
        <div>
            {0}
        </div>
        <p>See <a href="{1}/app/users/{2}/report.pdf/">User Report</a></p>
    """.format(''.join(contents), settings.SITE_URL, user_id)

    return message


def get_message_pis_missing_trainings(contents):
    """ Get a message for PIs """

    message = """\
        <p>Please be advised that the following users have missing required training certification(s) for your area. Kindly review the list and ensure appropriate actions are taken.</p>
        <div>
            {0}
        </div>
        <p>Let us know if you need any further details or assistance.</p>
    """.format(contents)

    return message



# Expired trainings

def get_users_with_expired_trainings(target_date, type):
    ''' Get users with expired trainings '''
    
    users = {}

    filters = Q(user__is_active=True) & ~Q(completion_date=F('expiry_date'))
    if type == 'before':
        filters &= Q(expiry_date=target_date)
    elif type == 'after':
        filters &= Q(expiry_date__lt=target_date)
    
    values = ['user', 'cert', 'user__first_name', 'user__last_name', 'user__email', 'cert__name']
    
    user_trainings = UserCert.objects.filter(filters).order_by('id').values(*values).annotate(latest_expiry_date=Max('expiry_date'))
    if user_trainings.exists():
        for ut in user_trainings.iterator():
            user_id = str(ut['user'])
            if user_id not in users.keys():
                users[user_id] = {
                    'id': user_id,
                    'first_name': ut['user__first_name'],
                    'last_name': ut['user__last_name'],
                    'email': ut['user__email'],
                    'expired_trainings': []
                }
            
            users[user_id]['expired_trainings'].append({
                'name': ut['cert__name'],
                'expiry_date': appFunc.convert_date_to_str(ut['latest_expiry_date'])
            })

    return users


def get_message_users_expired_trainings(user_id, trainings, days, type):
    """ Get a message with a list of users for lab users """

    contents = []
    for tr in trainings:
        content = '<li>{0} (Expiry Date: {1})</li>'.format(tr['name'], tr['expiry_date'])
        contents.append(content)

    message = ''
    if type == 'before':
        message = """\
        <p>This is a friendly reminder that one or more of your trainings will expire in {0} days. Please update these certificates at your earliest convenience.</p>
        <ul>{1}</ul>
        <p>See <a href='{2}/app/users/{3}/report.pdf/'>User Report</a></p>
        """.format(days, ''.join(contents), settings.SITE_URL, user_id)
    
    elif type == 'after':
        message = """\
        <p>This is a friendly reminder that your training has passed its expiration date. Please log in and update your training as soon as possible.</p>
        <ul>{0}</ul>
        <p>See <a href='{1}/app/users/{2}/report.pdf/'>User Report</a></p>
        """.format(''.join(contents), settings.SITE_URL, user_id)

    return message


def get_message_pis_expired_trainings(contents, days, type):
    """ Get a message with a list of users """

    message = ''
    if type == 'before':
        message = """\
            <p>Please be advised that the training certifications for the following users in your area will expire in {0} days. Please remind these individuals to complete the necessary renewal process before their certifications expire.</p>
            <div>
                {1}
            </div>
        """.format(days, contents)
    
    elif type == 'after':
        message = """\
            <p>Please be advised that the training certifications for the following users in your area have already expired. Please remind them to complete their renewal at the earliest convenience to prevent any area access issues.</p>
            <div>
                {0}
            </div>
        """.format(contents)

    return message


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
        <div>
            {2}
        </div>
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
                <a href="https://my.landfood.ubc.ca/lfs-intranet/onboarding/lfs-mandatory-training/">https://my.landfood.ubc.ca/lfs-intranet/onboarding/lfs-mandatory-training/</a>
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



# API service


def get_next_url(curr_page):
    return '{0}?page={1}&pageSize={2}'.format(settings.LFS_LAB_CERT_TRACKER_API_URL, curr_page, 50)


def get_expiry_date(completion_date, cert):
    expiry_year = completion_date.year + int(cert.expiry_in_years)
    return date(year=expiry_year, month=completion_date.month, day=completion_date.day)


def pull_by_api(headers, usernames, form_checking, multiple_trainings):
    user_trainings = []
    
    body = {'requestIdentifiers': [{'identifierType': 'CWL', 'identifier': username} for username in usernames]}
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
            training_id = str(item['certificate']['trainingId']).strip()
            completion_date = item['certificate']['completionDate'].split('T')[0].split('-')

            if item['certificate']['status'] == 'active' and len(completion_date) == 3:
                completion_date = date(year=int(completion_date[0]), month=int(completion_date[1]), day=int(completion_date[2]))
                user = appFunc.get_user_by_username(username)

                training = None
                found_training = Cert.objects.filter(unique_id__iexact=training_id)                
                if found_training.exists():
                    training = found_training.first()
                else:
                    if multiple_trainings.exists():
                        for tr in multiple_trainings:
                            unique_ids = tr.unique_id.split(',')
                            for uid in unique_ids:
                                if training_id == uid.strip():
                                    training = tr
                                    break
                            if training:
                                break
                
                if user and training:
                    form = '{0}_{1}_{2}'.format(user.id, training.id, completion_date)
                    user_certs = user.usercert_set.filter(cert_id=training.id, completion_date=completion_date)
                    if not user_certs.exists() and form not in form_checking:
                        user_trainings.append(UserCert(
                            user = user,
                            cert = training,
                            cert_file = 'None',
                            uploaded_date = date.today(),
                            completion_date = completion_date,
                            expiry_date = get_expiry_date(completion_date, training),
                            by_api = True
                        ))

                        form_checking.append(form)                        
            else:
                print('Warning: completion date is wrong, or status is not active:', username, training_name)
        
        hasNextPage = json['hasNextPage']
        next_url = get_next_url(int(json['page']) + 1)
    
    return user_trainings, form_checking


# def find_cert(training_name):
#     if training_name == 'Chemical Safety' or training_name == 'Chemical Safety Refresher':
#         training_name = 'Chemical Safety/Chemical Safety Refresher'
#     elif training_name == 'Biosafety for Study Team Members' or training_name == 'Biosafety Refresher for Study Team Members':
#         training_name = 'Biosafety for Study Team Members/Biosafety Refresher for Study Team Members'
#     elif training_name == 'Biosafety for Permit Holders' or training_name == 'Biosafety Refresher for Permit Holders':
#         training_name = 'Biosafety for Permit Holders/Biosafety Refresher for Permit Holders'
#     elif training_name == 'Transportation of Dangerous Goods by Ground and Air_ April 2020- March 7 2022':
#         training_name = 'Transportation of Dangerous Goods by Ground and Air'
#     elif training_name == "Remote Work. Home Office Ergonomics. Orientation":
#         training_name = "Home Office Ergo"

#     cert = Cert.objects.filter(name=training_name)    
#     return cert.first() if cert.exists() else None