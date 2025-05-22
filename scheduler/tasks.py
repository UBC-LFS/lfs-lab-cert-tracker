from django.conf import settings
from datetime import date, datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.paginator import Paginator
from django.db.models import Q, F, Max

from django.contrib.auth.models import User
from lfs_lab_cert_tracker.models import UserCert, Lab, UserLab, Cert
from app import functions as appFunc
from . import functions as func


# Users

def send_to_users(users, path, days=None, type=None):
    ''' Send it to users '''

    if len(users.keys()) > 0:
        for user_id in users.keys():
            user = users[user_id]
            if appFunc.check_email_valid(user['email']):
                receiver = func.get_receiver(user['first_name'], user['last_name'], user['email'])
                message = ''

                if path == 'missing':
                    message = func.get_message_users_missing_trainings(user_id, user['areas'])

                elif path == 'expired':
                    message = func.get_message_users_expired_trainings(user_id, user['expired_trainings'], days, type)
                
                if receiver and message:
                    template = func.html_template(user['first_name'], user['last_name'], message)
                    # func.send_email(receiver, template)
            else:
                print('{} is not valid.'.format(user['email']))
            
        print( 'User: Sent it to each user. (Note: total users: {0})'.format(len(users.keys())) )


def send_missing_trainings_users():
    ''' Send an email to users if they have missing trainings '''

    users, _ = func.get_users_missing_trainings()
    send_to_users(users, 'missing')
    

def send_before_expiry_date_users():
    ''' Send an email to users 1 month (30 days) BEFORE users' trainings expire '''

    days = 30
    target_date = datetime.now() + timedelta(days=days)
    # target_date = datetime(2019, 6, 14) + timedelta(days=days) # for testing

    users = func.get_users_with_expired_trainings(target_date, 'before')
    send_to_users(users, 'expired', days, 'before')


def send_after_expiry_date_users():
    ''' Send an email to users if they have expired trainings '''
    
    users = func.get_users_with_expired_trainings(date.today(), 'after')
    send_to_users(users, 'expired', 14, 'after')


# Pis

def send_missing_trainings_pis():
    ''' Send an email to PIs if users have missing trainings in their areas '''

    users, areas = func.get_users_missing_trainings()
    memo = {}
    if len(users.keys()) > 0 and len(areas.keys()) > 0:
        pis = UserLab.objects.filter(role=1, user__is_active=True).select_related('user', 'lab')
        if pis.exists():
            for pi in pis.iterator():
                area_id = str(pi.lab.id)                
                if area_id in areas.keys():

                    contents = []
                    if area_id in memo.keys():
                        contents = memo[area_id]
                    else:
                        for user_id in areas[area_id].keys():
                            user = areas[area_id][user_id]
                            content = '<p><u>' + user['full_name'] + '</u></p><ul>'
                            for trainings in user['missing_trainings']:
                                content += '<li>{0}</li>'.format(trainings)
                            content += '</ul>'
                            contents.append(content)

                        memo[area_id] = contents
                
                    receiver = func.get_receiver(pi.user.first_name, pi.user.last_name, pi.user.email)
                    message = func.get_message_pis_missing_trainings(''.join(contents))
                    if receiver and message:
                        template = func.html_template(pi.user.first_name, pi.user.last_name, message)
                        # func.send_email(receiver, template)
                        print('Supervisor: Sent it to {0}'.format(receiver))


def send_to_pis(target_day, days, type):
    ''' Send it to Pis '''
    
    filters = Q(user__is_active=True) & ~Q(completion_date=F('expiry_date')) & Q(user__userlab__lab=area.id) & Q(cert__labcert__lab=area.id)
    if type == 'before':
        filters &= Q(expiry_date=target_day)
    elif type == 'after':
        filters &= Q(expiry_date__lt=target_day)

    values = ['user', 'cert', 'user__first_name', 'user__last_name', 'cert__name']

    for area in Lab.objects.all():
        users = {}

        user_trainings = UserCert.objects.filter(filters).order_by('id').values(*values).annotate(latest_expiry_date=Max('expiry_date'))
        if user_trainings.exists():
            for ut in user_trainings.iterator():
                user_id = ut['user']
                if user_id not in users.keys():
                    users[user_id] = {
                        'first_name': ut['user__first_name'],
                        'last_name': ut['user__last_name'],
                        'trainings': []
                    }
                users[user_id]['trainings'].append({
                    'name': ut['cert__name'],
                    'expiry_date': appFunc.convert_date_to_str(ut['latest_expiry_date'])
                })

        contents = []        
        if len(users.keys()) > 0:
            for user_id in users.keys():
                user = users[user_id]
                content = '<p><u>' + user['first_name'] + ' ' + user['last_name'] + '</u></p><ul>'
                for tr in user['trainings']:
                    content += '<li>{0} (Expiry Date: {1})</li>'.format(tr['name'], tr['expiry_date'])
                content += '</ul>'
                contents.append(content)

        if len(contents) > 0:
            pis = UserLab.objects.filter(lab_id=area.id, role=1)
            if pis.exists():
                for pi in pis:
                    receiver = func.get_receiver(pi.user.first_name, pi.user.last_name, pi.user.email)
                    message = func.get_message_pis_expired_trainings(''.join(contents), days, type)
                    if receiver and message:
                        template = func.html_template(pi.user.first_name, pi.user.last_name, message)
                        # func.send_email(receiver, template)
                        print('Supervisor: Sent it to {0}'.format(pi.user.email))


def send_before_expiry_date_pis():
    ''' Send an email to PIs 1 month (30 days) BEFORE Users' trainings expire '''
    
    days = 30
    target_date = datetime.now() + timedelta(days=days)
    send_to_pis(target_date, days, 'before')


def send_after_expiry_date_pis():
    ''' Send an email to Pis if Users have expired trainings '''

    send_to_pis(date.today(), 14, 'after')


# Admins

def send_to_admins(target_date, days, type):
    ''' Send it to Admins '''

    users = func.get_users_with_expired_trainings(target_date, type)
    if len(users.keys()) > 0:
        contents = []
        for user_id in users.keys():
            user = users[user_id]
            content = '<div>{0} {1} (<a href="{2}/app/users/{3}/report.pdf/">User Report</a>)</div><ul>'.format(user['first_name'], user['last_name'], settings.SITE_URL, str(user_id))
            for tr in user['expired_trainings']:
                content += '<li>{0} (Expiry Date: {1})</li>'.format(tr['name'], tr['expiry_date'])
            content += '</ul>'
            contents.append(content)
        
        admins = User.objects.filter(is_active=True, is_superuser=True)
        if admins.exists():
            for admin in admins.iterator():
                if appFunc.check_email_valid(user['email']):
                    receiver = func.get_receiver(admin.first_name, admin.last_name, admin.email)
                    message = func.get_message_pis_expired_trainings(''.join(contents), days, type)
                    if receiver and message:
                        template = func.html_template('LFS TRMS', 'administrators', message)
                        # func.send_email(receiver, template)
                        print( 'Admin: Sent it to {0}'.format(admin.email) )


def send_before_expiry_date_admins():
    ''' Send an email to Admins 2 weeks (14 days) BEFORE Users' trainings expire '''

    days = 14
    target_date = datetime.now() + timedelta(days=days)
    send_to_admins(target_date, days, 'before')


def send_after_expiry_date_admins():
    ''' Send an email to Admins AFTER Users' training expiration date '''

    send_to_admins(date.today(), 14, 'after')


# API service

def check_user_trainings_by_api():
    headers = { 
        'X-Client-Id': settings.LFS_LAB_CERT_TRACKER_CLIENT_ID, 
        'X-Client-Secret': settings.LFS_LAB_CERT_TRACKER_CLIENT_SECRET 
    }

    users = appFunc.get_users('active')
    usernames = []
    for user in users.iterator():
        missing_certs = appFunc.get_user_missing_certs(user.id)
        expired_certs = appFunc.get_user_expired_certs(user)
        if len(missing_certs) > 0 or len(expired_certs) > 0:
            usernames.append(user.username)

    if len(usernames) > 0:
        multiple_trainings = Cert.objects.filter(unique_id__icontains=',')
        paginator = Paginator(usernames, 5)

        user_trainings = []
        form_checking = []
        has_next = True
        i = 1
        while has_next:
            sub_usernames = paginator.page(i)
            items, forms = func.pull_by_api(headers, sub_usernames, form_checking, multiple_trainings)
            user_trainings += items
            form_checking = forms
            has_next = sub_usernames.has_next()
            i += 1
        
        UserCert.objects.bulk_create(user_trainings)
        print('The number of user trainings have been updated:', len(user_trainings))
    else:
        print('API Calls: No users found to update')


def run():
    print('Scheduling tasks running...')

    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)

    # Before expiry date

    # Monday ~ Friday at 9:00 AM
    scheduler.add_job(send_before_expiry_date_users, 'cron', day_of_week='mon-fri', hour=9, minute=0)

    # Monday ~ Friday at 9:30 AM
    scheduler.add_job(send_before_expiry_date_pis, 'cron', day_of_week='mon-fri', hour=9, minute=30)

    # Monday ~ Friday at 10:00 AM
    scheduler.add_job(send_before_expiry_date_admins, 'cron', day_of_week='mon-fri', hour=10, minute=0)


    # After expiry date

    # 1st Monday, 3rd Monday at 9:00 AM
    scheduler.add_job(send_after_expiry_date_users, 'cron', day='1st mon,3rd mon', hour=9, minute=0)

    # 1st Monday, 3rd Monday at 9:30 AM
    scheduler.add_job(send_after_expiry_date_pis, 'cron', day='1st mon,3rd mon', hour=9, minute=30)

    # 1st Monday, 3rd Monday at 10:00 AM
    scheduler.add_job(send_after_expiry_date_admins, 'cron', day='1st mon,3rd mon', hour=10, minute=0)


    # Missing

    # 1st Monday, 3rd Monday at 9:00 AM
    scheduler.add_job(send_missing_trainings_users, 'cron', day='1st mon,3rd mon', hour=9, minute=0)

    # 1st Monday, 3rd Monday at 9:30 AM
    scheduler.add_job(send_missing_trainings_pis, 'cron', day='1st mon,3rd mon', hour=9, minute=30)


    # Monday ~ Sunday at 3:00 AM
    scheduler.add_job(check_user_trainings_by_api, 'cron', day_of_week='mon-sun', hour=3, minute=0)

    scheduler.start()