from django.conf import settings
from datetime import date, datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.paginator import Paginator
from django.db.models import Q, F, Max, OuterRef, Subquery, Exists

from django.contrib.auth.models import User
from lfs_lab_cert_tracker.models import UserCert, Lab, UserLab, LabCert
from app import functions as appFunc
from . import functions as func

DAYS30 = 30
DAYS14 = 14


def get_users_with_expired_trainings(target_date):
    ''' Get users with expired trainings '''

    user_trainings = UserCert.objects.filter(
        Q(expiry_date__lt=target_date) & 
        ~Q(completion_date=F('expiry_date'))
    ).values(
        'user', 
        'cert', 
        'user__first_name', 
        'user__last_name', 
        'user__email', 
        'cert__name'
    ).annotate(latest_expiry_date=Max('expiry_date'))
    
    users = {}
    for ut in user_trainings:
        user_id = str(ut['user'])
        if user_id not in users.keys():
            users[user_id] = {
                'id': user_id,
                'first_name': ut['user__first_name'],
                'last_name': ut['user__last_name'],
                'email': ut['user__email'],
                'trainings': []
            }
        
        users[user_id]['trainings'].append({
            'name': ut['cert__name'],
            'expiry_date': appFunc.convert_date_to_str(ut['latest_expiry_date'])
        })

    return users


def send_to_users(users, path, days=None, type=None):
    ''' Send it to users '''

    for user_id in users.keys():
        user = users[user_id]
        

        if appFunc.check_email_valid(user['email']):
            receiver = func.get_receiver(user['first_name'], user['last_name'], user['email'])

            if path == 'missing':
                message = func.get_message_users_missing_trainings(user_id, user['missing_trainings'])

            elif path == 'expired':
                message = func.get_message_users_expired_trainings(user_id, user['expired_trainings'], days, type)

            if receiver and message:
                template = func.html_template(user['first_name'], user['last_name'], message)
                # func.send_email(receiver, template)
        
        print( 'User: Sent it to each user. (Note: total users: {0})'.format(len(users.keys())) )


def send_to_pis(target_day, days=None, type=None):
    '''  '''
    for area in Lab.objects.all():
        pis = UserLab.objects.filter(lab_id=area.id, role=1)
        if pis.exists():
            user_trainings = UserCert.objects.filter(
                Q(expiry_date__lt=target_day) & 
                ~Q(completion_date=F('expiry_date')) & 
                Q(user__userlab__lab=area.id) & 
                Q(cert__labcert__lab=area.id)
            ).values(
                'user', 
                'cert',
                'user__first_name', 
                'user__last_name',
                'cert__name'
            ).annotate(latest_expiry_date=Max('expiry_date'))

            users = {}
            for ut in user_trainings:
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
            for user_id in users.keys():
                user = users[user_id]

                content = '<p>' + user['first_name'] + ' ' + user['last_name'] + '</p><ul>'
                for tr in user['trainings']:
                    content += '<li>{0} (Expiry Date: {1})</li>'.format(tr['name'], tr['expiry_date'])
                content += '</ul>'
                contents.append(content)

            for pi in pis:
                receiver = func.get_receiver(pi.user.first_name, pi.user.last_name, pi.user.email)
                message = func.get_message_pis_expired_trainings(''.join(contents), days, type)
                template = func.html_template(pi.user.first_name, pi.user.last_name, message)

                # func.send_email(receiver, template)
                print('Supervisor: Sent it to {0}'.format(pi.user.email))



def send_to_admins(target_date, days, type):
    ''' Send it to Admins '''

    users = get_users_with_expired_trainings(target_date)

    if len(users.keys()) > 0:
        admins = User.objects.filter(is_active=True, is_superuser=True)
        if len(admins) > 0:
            contents = []
            for user_id in users.keys():
                user = users[user_id]

                content = '<div>{0} {1}(<a href="{2}/app/users/{3}/report.pdf/">User Report</a>)</div><ul>'.format(user['first_name'], user['last_name'], settings.SITE_URL, str(user_id))
                for tr in user['trainings']:
                    content += '<li>{0} (Expiry Date: {1})</li>'.format(tr['name'], tr['expiry_date'])
                content += '</ul>'
                contents.append(content)
            
            contents_list = ''.join(contents)

            for admin in admins:
                if appFunc.check_email_valid(user['email']):
                    receiver = func.get_receiver(admin.first_name, admin.last_name, admin.email)
                    message = func.get_message_pis_expired_trainings(contents_list, days, type)
                    template = func.html_template('LFS TRMS', 'administrators', message)

                    # func.send_email(receiver, template)
                    print( 'Admin: Sent it to {0}'.format(admin.email) )


def send_before_expiry_date_users():
    ''' Send an email to lab users who have expired trainings 1 month prior to expiry date '''

    days = 30
    target_date = datetime.now() + timedelta(days=days)
    # target_date = datetime(2019, 6, 14) + timedelta(days=days) # for testing
    
    users = get_users_with_expired_trainings(target_date)
    if len(users.keys()) > 0:
        send_to_users(users, days, 'before')

    
def send_before_expiry_date_pis():
    '''  '''
    
    days = 30
    target_date = datetime.now() + timedelta(days=days)
    send_to_pis(target_date, days, 'before')


def send_before_expiry_date_admins():
    '''  '''

    days = 14
    target_date = datetime.now() + timedelta(days=days)
    send_to_admins(target_date, days, 'before')


def send_after_expiry_date_users():
    ''' Send an email to users if they have expired trainings '''
    
    users = get_users_with_expired_trainings(date.today())
    if len(users.keys()) > 0:
        send_to_users(users, 14, 'after')
    


def send_after_expiry_date_pis():
    ''' Send an email to Pis if they have expired trainings '''

    send_to_pis(date.today(), 14, 'after')


def send_after_expiry_date_admins():
    ''' Send an email to admins if users have expired trainings '''

    send_to_admins(date.today(), 14, 'after')


def get_users_missing_trainings():
    '''  '''

    has_cert_subquery = UserCert.objects.filter(user=OuterRef('user'), cert=OuterRef('cert'))
    area_trainings = LabCert.objects.filter(lab__userlab__user__isnull=False).annotate(
        user=F('lab__userlab__user'),
        first_name=F('lab__userlab__user__first_name'),
        last_name=F('lab__userlab__user__last_name')
    ).filter(~Exists(has_cert_subquery)).values(
        'user', 
        'lab',
        'cert', 
        'lab__name', 
        'cert__name',
        'first_name',
        'last_name'
    ).distinct()

    users = {}
    areas = {}
    if area_trainings.exists():
        for at in area_trainings:
            user_id = str(at['user'])
            area_id = str(at['lab'])
            area = '{0}|{1}'.format(at['lab'], at['lab__name'])

            if user_id not in users.keys():
                users[user_id] = {
                    'first_name': at['first_name'],
                    'last_name': at['last_name']
                }
            
            if area not in users[user_id].keys():
                users[user_id][area] = {
                    'name': at['lab__name'],
                    'missing_trainings': []
                }
            users[user_id][area]['missing_trainings'].append(at['cert__name'])

            if area_id not in areas.keys():
                areas[area_id] = {}

            if user_id not in areas[area_id].keys():
                areas[area_id][user_id] = {
                    'full_name': '{0} {1}'.format(at['first_name'], at['last_name']),
                    'missing_trainings': []
                }

            areas[area_id][user_id]['missing_trainings'].append(at['cert__name'])
    
    return users, areas


def send_missing_trainings_users():
    '''  '''

    users = get_users_missing_trainings()
    if len(users.keys()):
        send_to_users(users)


def send_missing_trainings_pis():
    '''  '''

    users, areas = get_users_missing_trainings()
    memo = {}

    if len(users.keys()) > 0 and len(areas) > 0:
        pis = UserLab.objects.filter(role=1).select_related('user', 'lab')
        if pis.exists():
            
            for pi in pis:
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
                    template = func.html_template(pi.user.first_name, pi.user.last_name, message)

                    # func.send_email(receiver, template)
                    print('Supervisor: Sent it to {0}'.format(receiver))

                        
            
                




def check_user_certs_by_api():
    headers = { 
        'X-Client-Id': settings.LFS_LAB_CERT_TRACKER_CLIENT_ID, 
        'X-Client-Secret': settings.LFS_LAB_CERT_TRACKER_CLIENT_SECRET 
    }

    certs = appFunc.get_certs()
    users = appFunc.get_users('active')
    usernames = []
    
    for user in users:
        missing_certs = appFunc.get_user_missing_certs(user.id)
        expired_certs = appFunc.get_user_expired_certs(user)
        if len(missing_certs) > 0 or len(expired_certs) > 0:
            usernames.append(user.username)
    
    if len(usernames) > 0:
        paginator = Paginator(usernames, 5)

        validation = []
        data = []
        has_next = True
        i = 1
        while has_next:
            sub_usernames = paginator.page(i)
            items, v = func.pull_by_api(headers, certs, sub_usernames, validation)
            data += items
            validation = v
            has_next = sub_usernames.has_next()
            i += 1

        UserCert.objects.bulk_create(data)
        print('Updated the number of user certs:', len(data))
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
    scheduler.add_job(check_user_certs_by_api, 'cron', day_of_week='mon-sun', hour=3, minute=0)

    scheduler.start()



# 1st Monday, 3rd Monday at 10:30 AM
# scheduler.add_job(send_after_expiry_date, 'cron', day='1st mon,3rd mon', hour=10, minute=30)

"""
def send_after_expiry_date2():
    ''' Send an email to all users if some expired trainings exist '''

    TYPE = 'after'

    target_day = date.today()
    # target_day = datetime(2020, 1, 1) # for testing

    active_users = User.objects.filter(is_active=True)
    lab_users, pis = func.find_expired_trainings(active_users, target_day, TYPE)
    if len(lab_users) > 0:
        func.send_email_to_lab_users(lab_users, DAYS14, TYPE)

        if len(pis.keys()) > 0:
            func.send_email_to_pis(pis, DAYS14, TYPE)
        
        admins = User.objects.filter(is_superuser=True)
        if len(admins) > 0:
            func.send_email_to_admins(admins, lab_users, DAYS14, TYPE)

    print('Done: send after expiry date')
"""

"""
def send_missing_trainings2():
    ''' Send an email to users who have missing trainings twice per month '''
    print('send_missing_trainings')

    lab_users, pis = func.find_missing_trainings()

    # Lab users
    for lab_user in lab_users:
        user_id = lab_user['id']
        user = appFunc.get_user_by_id(user_id)

        receiver = func.get_receiver(user)
        message = func.get_message_lab_users_missing_trainings(user_id, lab_user['missing_trainings'])
        template = func.html_template(user.first_name, user.last_name, message)

        func.send_email(receiver, template)
        print( 'User: Sent it to {0}'.format(receiver) )


    # PIs
    for id, lab_users in pis.items():
        if len(lab_users) > 0:
            user = appFunc.get_user_by_id(id)

            receiver = func.get_receiver(user)
            message = func.get_message_pis_missing_trainings(lab_users)
            template = func.html_template(user.first_name, user.last_name, message)

            func.send_email(receiver, template)
            print( 'Supervisor: Sent it to {0}'.format(receiver) )

    print('Done: send missing trainings')
"""