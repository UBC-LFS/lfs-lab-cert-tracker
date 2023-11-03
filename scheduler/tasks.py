from django.conf import settings
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.paginator import Paginator

from app.functions import *
from .functions import *

DAYS30 = 30
DAYS14 = 14


def send_missing_trainings():
    ''' Send an email to users who have missing trainings twice per month '''
    print('send_missing_trainings')

    lab_users, pis = find_missing_trainings()

    # Lab users
    for lab_user in lab_users:
        user_id = lab_user['id']
        user = get_user_by_id(user_id)

        receiver = get_receiver(user)
        message = get_message_lab_users_missing_trainings(user_id, lab_user['missing_trainings'])
        template = html_template(user.first_name, user.last_name, message)

        send_email(receiver, template)
        print( 'User: Sent it to {0}'.format(receiver) )


    # PIs
    for id, lab_users in pis.items():
        if len(lab_users) > 0:
            user = get_user_by_id(id)

            receiver = get_receiver(user)
            message = get_message_pis_missing_trainings(lab_users)
            template = html_template(user.first_name, user.last_name, message)

            send_email(receiver, template)
            print( 'Supervisor: Sent it to {0}'.format(receiver) )

    print('Done: send missing trainings')


def send_before_expiry_date_user_pi():
    '''
    Send an email to lab users and PIs who have expired trainings 1 month prior to expiry date
    Note: A PI represents a Principal Investigator
    '''

    TYPE = 'before'

    # target_day = datetime(2019, 6, 14) + timedelta(days=DAYS30) # for testing
    target_day = datetime.now() + timedelta(days=DAYS30)

    lab_users, pis = find_expired_trainings(target_day.date(), TYPE)

    # to Lab users
    if len(lab_users) > 0:
        send_email_to_lab_users(lab_users, DAYS30, TYPE)

        # to PIs
        if len(pis.keys()) > 0:
            send_email_to_pis(pis, DAYS30, TYPE)

    print('Done: send it 30 days before the expiry date')


def send_before_expiry_date_admin():
    ''' Send an email to admins who have expired trainings 2 weeks before the expiry date '''

    TYPE = 'before'

    # target_day = datetime(2019, 6, 30) + timedelta(days=DAYS14)  # for testing
    target_day = datetime.now() + timedelta(days=DAYS14)

    lab_users, _ = find_expired_trainings(target_day.date(), TYPE)
    admins = get_admins()

    if len(lab_users) > 0 and len(admins) > 0:
        send_email_to_admins(admins, lab_users, DAYS14, TYPE)

    print('Done: send it 14 days before the expiry date')


def send_after_expiry_date():
    ''' Send an email to all users if some expired trainings exist '''

    TYPE = 'after'

    target_day = datetime.now()
    # target_day = datetime(2020, 1, 1) # for testing

    admins = get_admins()
    lab_users, pis = find_expired_trainings(target_day.date(), TYPE)

    if len(lab_users) > 0:
        send_email_to_lab_users(lab_users, DAYS14, TYPE)

        if len(pis.keys()) > 0:
            send_email_to_pis(pis, DAYS14, TYPE)

        if len(admins) > 0:
            send_email_to_admins(admins, lab_users, DAYS14, TYPE)

    print('Done: send after expiry date')


def check_user_certs_by_api():
    headers = { 
        'X-Client-Id': settings.LFS_LAB_CERT_TRACKER_CLIENT_ID, 
        'X-Client-Secret': settings.LFS_LAB_CERT_TRACKER_CLIENT_SECRET 
    }

    certs = get_certs()
    users = get_users('active')
    usernames = []
    for user in users:
        missing_certs = get_user_missing_certs(user.id)
        expired_certs = get_user_expired_certs(user.id)
        if len(missing_certs) > 0 or len(expired_certs) > 0:
            usernames.append(user.username)

    paginator = Paginator(usernames, 20)

    data = []
    has_next = True
    i = 1
    while has_next:
        sub_usernames = paginator.page(i)
        items = pull_by_api(headers, certs, sub_usernames)
        data += items
        has_next = sub_usernames.has_next()
        i += 1

    UserCert.objects.bulk_create(data)
    print('Updated the number of user certs:', len(data))


def run():
    print('Scheduling tasks running...')

    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)

    # 1st Monday, 3rd Monday at 10:00 AM
    scheduler.add_job(send_missing_trainings, 'cron', day='1st mon,3rd mon', hour=10, minute=0)

    # 1st Monday, 3rd Monday at 10:30 AM
    scheduler.add_job(send_after_expiry_date, 'cron', day='1st mon,3rd mon', hour=10, minute=30)

    # Monday ~ Friday at 11:00 AM
    scheduler.add_job(send_before_expiry_date_user_pi, 'cron', day_of_week='mon-fri', hour=11, minute=0)

    # Monday ~ Friday at 11:30 AM
    scheduler.add_job(send_before_expiry_date_admin, 'cron', day_of_week='mon-fri', hour=11, minute=30)

    # Monday ~ Sunday at 3:00 AM
    scheduler.add_job(check_user_certs_by_api, 'cron', day_of_week='mon-sun', hour=14, minute=40)

    scheduler.start()