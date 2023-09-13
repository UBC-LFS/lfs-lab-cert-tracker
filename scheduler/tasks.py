from django.conf import settings
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.paginator import Paginator

from app.functions import *
from .functions import *

from app.utils import Api, Notification

DAYS30 = 30
DAYS14 = 14

api = Api()
notification = Notification()

def send_missing_trainings():
    ''' Send an email to users who have missing trainings twice per month '''
    print('send_missing_trainings')

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
            message = notification.get_message_pis_missing_trainings(lab_users)
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

    # target_day = datetime(2019, 6, 14) + timedelta(days=DAYS30) # for testing
    target_day = datetime.now() + timedelta(days=DAYS30)

    lab_users, pis = notification.find_expired_trainings(target_day.date(), TYPE)

    # to Lab users
    if len(lab_users) > 0:
        notification.send_email_to_lab_users(lab_users, DAYS30, TYPE)

        # to PIs
        if len(pis.keys()) > 0:
            notification.send_email_to_pis(pis, DAYS30, TYPE)

    print('Done: send it 30 days before the expiry date')


def send_before_expiry_date_admin():
    ''' Send an email to admins who have expired trainings 2 weeks before the expiry date '''

    TYPE = 'before'

    # target_day = datetime(2019, 6, 30) + timedelta(days=DAYS14)  # for testing
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
    # target_day = datetime(2020, 1, 1) # for testing

    admins = api.get_admins()
    lab_users, pis = notification.find_expired_trainings(target_day.date(), TYPE)

    if len(lab_users) > 0:
        notification.send_email_to_lab_users(lab_users, DAYS14, TYPE)

        if len(pis.keys()) > 0:
            notification.send_email_to_pis(pis, DAYS14, TYPE)

        if len(admins) > 0:
            notification.send_email_to_admins(admins, lab_users, DAYS14, TYPE)

    print('Done: send after expiry date')


import requests

def get_next_url(curr_page):
    return '{0}?page={1}&pageSize={2}'.format(settings.LFS_LAB_CERT_TRACKER_API_URL, curr_page, 50)


def check_user_certs_by_api():
    print('check_user_certs_by_api')

    headers = { 
        'X-Client-Id': settings.LFS_LAB_CERT_TRACKER_CLIENT_ID, 
        'X-Client-Secret': settings.LFS_LAB_CERT_TRACKER_CLIENT_SECRET 
    }

    certs = get_certs()
    user_list = get_users('active')
    paginator = Paginator(user_list, 50)

    data = []
    training_names = set()

    has_next = True
    i = 1
    while has_next:
        users = paginator.page(i)
        print(i, len(users))

        usernames = []
        for user in users:
            missing_certs = get_user_missing_certs(user.id)
            if len(missing_certs) > 0:
                usernames.append(user.username)
        
        if len(usernames) > 0:
            items, tr_names = pull_by_api(headers, certs, usernames)
            data += items
            training_names = training_names.union(tr_names)
        
        has_next = users.has_next()
        i += 1

        if i == 10:
            break

    print(data)
    print(training_names)
    #uc = UserCert.objects.bulk_create(data)
    #print('done', uc)


    """usernames = []
    for user in get_users('active'):
        missing_certs = get_user_missing_certs(user.id)
        if len(missing_certs) > 0:
            usernames.append(user.username)

    #usernames = ['esanpi14', 'pabram','ackerman','mbejaei','berchs','rburlako','mackay3','lcomea01','mdossett','upadh','sdelder','tforge','isman','veirad','ariseman','lokyee','rtremb02','ejovel','jgrenz','mitch01','mariac1','rushenj','jrthomp','wahbe','bwalla01','gpassaia','hs55555','wtamagi','eseow','imeldac',"epaniak","jkc912","chili916","anjuerem","julianne","delaniea","gc3208","igalat","sandland","aachilli","fzheng20","leonar04","abruno13","yanga02","uv26","hrstens","juliaev","caslee","chery14","jujulia","stir24","sescal01","mcao9","kiran07","dhanush9","jennie20","yifeiw8","may0506","jacobp15","djosep01","tompix2","naskwaw","prs12ubc","cphelps4","cdemarti","cs2022","jim2901","reillyjp","jproct02","ayrafaiz","vlad","mayajb17","wkang01","hugh01"]
    #usernames = ['hs55555','wtamagi','eseow','imeldac']
    #usernames = ['hs55555']    
    #usernames = usernames[:50]
    #print(len(usernames))"""


def pull_by_api(headers, certs, usernames):
    data = []
    training_names = set()
    
    body = { 'requestIdentifiers': [{ 'identifierType': 'CWL', 'identifier': username } for username in usernames] }
    next_url = get_next_url(1)
    hasNextPage = True
    while hasNextPage:
        res = requests.post(next_url, json=body, headers=headers)
        if res.status_code == 500:
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
                #cert = Cert.objects.filter(name=training_name)

                if cert:
                    print(training_name, cert.name)

                training_names.add(training_name)

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
    
    return data, training_names


def run():
    print('Scheduling tasks running...')

    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)

    # 1st Monday, 3rd Monday at 10:00 AM
    #scheduler.add_job(send_missing_trainings, 'cron', day='1st mon,3rd mon', hour=10, minute=0)

    # 1st Monday, 3rd Monday at 10:30 AM
    #scheduler.add_job(send_after_expiry_date, 'cron', day='1st mon,3rd mon', hour=10, minute=30)

    # Monday ~ Friday at 11:00 AM
    #scheduler.add_job(send_before_expiry_date_user_pi, 'cron', day_of_week='mon-fri', hour=11, minute=0)

    # Monday ~ Friday at 11:30 AM
    #scheduler.add_job(send_before_expiry_date_admin, 'cron', day_of_week='mon-fri', hour=11, minute=30)

    # Monday ~ Sunday at 1:00 AM
    #scheduler.add_job(check_user_certs_by_api, 'cron', day_of_week='mon-sun', hour=1, minute=0)

    scheduler.start()