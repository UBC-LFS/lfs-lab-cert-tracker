from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

from lfs_lab_cert_tracker.utils import Api, Notification

DAYS30 = 30
DAYS14 = 14

api = Api()
notification = Notification()

def send_missing_trainings():
    ''' Send an email to users who have missing trainings twice per month '''

    lab_users, pis = notification.find_missing_trainings()

    # Lab users
    for lab_user in lab_users:
        user_id = lab_user['id']
        user = api.get_user(user_id)

        receiver = notification.get_receiver(user)
        message = notification.get_message_lab_users_missing_trainings(user_id, lab_user['missing_trainings'])
        template = notification.html_template(user.first_name, user.last_name, message)

        notification.send_email(receiver, template)
        print( 'User: Sent it to {0}'.format(receiver) )


    # PIs
    for id, lab_users in pis.items():
        if len(lab_users) > 0:
            user = api.get_user(id)

            receiver = notification.get_receiver(user)
            message = notification.get_message_pis_missing_trainings(users, lab_users)
            template = notification.html_template(user.first_name, user.last_name, message)

            notification.send_email(receiver, template)
            print( 'Supervisor: Sent it to {0}'.format(receiver) )

    print('Done: send missing trainings')


def send_before_expiry_date_user_pi():
    '''
    Send an email to lab users and PIs who have expired trainings 1 month prior to expiry date
    Note: A PI represents a Principal Investigator
    '''

    TYPE = 'before'

    #target_day = datetime(2019, 6, 14) + timedelta(days=DAYS30)
    target_day = datetime.now() + timedelta(days=DAYS30)
    lab_users, pis = notification.find_expired_trainings(target_day.date(), TYPE)

    # to Lab users
    if len(lab_users) > 0:
        notification.send_email_to_lab_users(lab_users, DAYS14, TYPE)

        # to PIs
        if len(pis.keys()) > 0:
            notification.send_email_to_pis(pis, DAYS14, TYPE)

    print('Done: send it 30 days before the expiry date')


def send_before_expiry_date_admin():
    ''' Send an email to admins who have expired trainings 2 weeks before the expiry date '''

    TYPE = 'before'

    #target_day = datetime(2019, 6, 30) + timedelta(days=DAYS14)
    target_day = datetime.now() + timedelta(days=DAYS14)

    lab_users, _ = notification.find_expired_trainings(target_day.date(), TYPE)
    admins = api.get_admins()

    if len(lab_users) > 0 and len(admins) > 0:
        notification.send_email_to_admins(admins, lab_users, DAYS14, TYPE)

    print('Done: send it 14 days before the expiry date')


def send_after_expiry_date():
    ''' Send an email to all users if some expired trainings exist '''

    TYPE = 'after'

    target_day = datetime.now()
    #target_day = datetime(2020, 1, 1)
    print("target_day: ", target_day)

    admins = api.get_admins()
    lab_users, pis = notification.find_expired_trainings(target_day.date(), TYPE)

    if len(lab_users) > 0:
        notification.send_email_to_lab_users(lab_users, DAYS14, TYPE)

        if len(pis.keys()) > 0:
            notification.send_email_to_pis(pis, DAYS14, TYPE)

        if len(admins) > 0:
            notification.send_email_to_admins(admins, lab_users, DAYS14, TYPE)

    print('Done: send after expiry date')


def run():
    print('Scheduling tasks running...')

    scheduler = BackgroundScheduler()

    scheduler.add_job(send_missing_trainings, 'cron', day_of_week='mon-fri', hour=16, minute=20) # 2 weeks
    scheduler.add_job(send_before_expiry_date_user_pi, 'cron', day_of_week='mon-fri', hour=16, minute=30) # everyday
    scheduler.add_job(send_before_expiry_date_admin, 'cron', day_of_week='mon-fri', hour=16, minute=40) # everyday
    scheduler.add_job(send_after_expiry_date, 'cron', day_of_week='mon-fri', hour=16, minute=50) # 2 weeks

    scheduler.start()
