from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db.models import Q, F, Max
from django.core.mail import send_mail
from django.urls import resolve

from django.contrib.auth.models import User
from lfs_lab_cert_tracker.models import *

from datetime import date


# User
def get_users(option=None):
    """ Get all users """
    if option == 'active':
        return User.objects.filter(is_active=True).order_by('last_name', 'first_name')
    return User.objects.all().order_by('last_name', 'first_name')

def get_user_by_id(user_id):
    return get_object_or_404(User, id=user_id)

def get_user_by_username(username):
    user = User.objects.filter(username=username)
    return user.first() if user.exists() else None

def get_user_name(user):
    curr_user = ''
    if user.first_name and user.last_name:
        curr_user = user.get_full_name()
    elif user.username:
        curr_user = user.username
    elif user.email:
        curr_user = user.email
    return curr_user


# UserCert

def get_user_certs(user):
    return user.usercert_set.all().distinct('cert__name')

def get_user_certs_with_info(user):
    check = []
    user_certs = []
    for uc in user.usercert_set.all().order_by('cert__name'):
        if uc.cert.id not in check:
            by_api = False
            user_cert = UserCert.objects.filter(user_id=user.id, cert_id=uc.cert.id, by_api=True)
            if user_cert.exists():
                by_api = True
            
            user_certs.append({
                'cert_id': uc.cert.id, 
                'cert_name': uc.cert.name,
                'by_api': by_api,
                'num_certs': UserCert.objects.filter(user_id=user.id, cert_id=uc.cert.id).count()
            })
            check.append(uc.cert.id)
    return user_certs

def get_user_missing_certs(user_id):
    required_certs = Cert.objects.filter(labcert__lab__userlab__user_id=user_id).distinct()
    certs = Cert.objects.filter(usercert__user_id=user_id).distinct()
    return required_certs.difference(certs).order_by('name')

def get_user_expired_certs(user):
    usercerts_with_max_expiry_date = user.usercert_set.values('cert_id').annotate(max_expiry_date=Max('expiry_date')).filter( Q(max_expiry_date__lt=date.today()) & ~Q(completion_date=F('expiry_date')) )
    return Cert.objects.filter(id__in=[item['cert_id'] for item in usercerts_with_max_expiry_date])


# UserLab


def get_user_labs(user, is_pi=False):
    if is_pi:
        return user.userlab_set.filter(role=UserLab.PRINCIPAL_INVESTIGATOR).order_by('lab__name')
    return user.userlab_set.all().order_by('lab__name')

def required_certs_in_lab(lab_id):
    return Cert.objects.filter(labcert__lab_id=lab_id).order_by('name')


# Cert

def get_certs():
    return Cert.objects.all()

def get_cert_by_id(cert_id):
    return get_object_or_404(Cert, id=cert_id)


# Lab

def is_pi_in_area(user_id, area_id):
    """ Check whether an user is in the area or not """

    return UserLab.objects.filter( Q(user=user_id) & Q(lab=area_id) & Q(role=UserLab.PRINCIPAL_INVESTIGATOR) ).exists()


def get_users_in_area_by_pi(user_id):
    """ Get a list of users in PI's area """

    users = set()

    userlabs = UserLab.objects.filter( Q(user_id=user_id) & Q(role=UserLab.PRINCIPAL_INVESTIGATOR) )
    if userlabs.exists():
        for userlab in userlabs:
            labs = UserLab.objects.filter(lab=userlab.lab.id)
            if labs.exists():
                for lab in labs:
                    users.add(lab.user.id)

    return list(users)


def get_lab_by_id(lab_id):
    return get_object_or_404(Lab, id=lab_id)


def update_or_create_areas_to_user(user, areas):
    """ update or create areas to an user """

    all_userlab = user.userlab_set.all()

    report = { 'updated': [], 'created': [], 'deleted': [] }
    used_areas = []
    for area in areas:
        splitted = area.split(',')
        lab = get_lab_by_id(splitted[0])
        role = splitted[1]
        userlab = all_userlab.filter(lab_id=lab.id)
        used_areas.append(lab.id)

        # update or create
        if userlab.exists():
            if userlab.first().role != int(role):
                updated = userlab.update(role=role)
                if updated:
                    report['updated'].append(lab.name)
        else:
            created = UserLab.objects.create(user=user, lab=lab, role=role)
            if created:
                report['created'].append(lab.name)

    for ul in all_userlab:
        if ul.lab.id not in used_areas:
            deleted = ul.delete()
            if deleted:
                report['deleted'].append(ul.lab.name)

    return report

# LabCert



def welcome_message():
    """ This is a welcome message"""

    return '''\
    <p>Welcome to LFS!</p>

    <p>
        Thank you for using the LFS Training Record Management System! We want to take this opportunity to introduce you to the <a href="https://my.landfood.ubc.ca/operations/health-and-safety/johsc/" target="_blank">LFS Joint Occupational Health and Safety Committee (JOHSC)</a> and our Local Safety Teams (LSTs). We hope you spend some time to familiarize yourself with your local area’s LST membership and contact information. Below are the four LSTs covering the health and safety of the four main buildings in our faculty:
    </p>

    <ul style="list-style-type:none;">
        <li>
        <a href="https://my.landfood.ubc.ca/operations/health-and-safety/macmillan-lst/" target="_blank">
            MacMillan Local Safety Team (MCML LST)
        </a>
        </li>
        <li>
        <a href="https://my.landfood.ubc.ca/operations/health-and-safety/fnh-lst/" target="_blank">
            Food Nutrition and Health Local Safety Team (FNH LST)
        </a>
        </li>
        <li>
        <a href="https://my.landfood.ubc.ca/operations/health-and-safety/ubc-farm-lst/" target="_blank">
            UBC Farm Local Safety Team (Farm LST)
        </a>
        </li>
        <li>Dairy Centre Local Safety Team (Dairy LST) – coming soon</li>
    </ul>

    <p>
        Thank you for going through all the mandatory health and safety training. What a champion! Please note that if you have not already done so, your supervisor should be reviewing any <a href="https://srs.ubc.ca/health-safety/research-safety/" target="_blank">additional specific training<a/> required for your work duties with you. Your LST may have some safety orientation that is mandatory specific to the building you work in so please check <a href="https://my.landfood.ubc.ca/operations/health-and-safety/lfs-mandatory-training/" target="_blank">mandatory training<a/> for guidelines. Please note that all mandatory training as well as any additional training records should be uploaded to <a href="https://training-report.landfood.ubc.ca" target="_blank">https://training-report.landfood.ubc.ca<a/> via your Campus Wide Login. To access the website off campus, please ensure you connect via <a href="https://it.ubc.ca/services/email-voice-internet/myvpn" target="_blank">UBC VPN</a>.
    </p>

    <p>
        To receive regular updates from our faculty, please subscribe to the appropriate <a href="https://my.landfood.ubc.ca/communications/communication-channels/" target="_blank">communication channels</a> below:
    </p>

    <ul>
        <li>
        LFS Today (Staff and Faculty):
        <a href="https://my.landfood.ubc.ca/lfs-today/" target="_blank">https://my.landfood.ubc.ca/lfs-today/</a>
        </li>
        <li>
        LFS Grad Student Listserve (Grad students):
        email <a href="mailto:lia.maria@ubc.ca">lia.maria@ubc.ca</a>
        </li>
        <li>
        Newslettuce (Undergraduates):
        email <a href="mailto:lfs.programassistant@ubc.ca">lfs.programassistant@ubc.ca</a>
        </li>
    </ul>

    <p>
        If you have any questions, please don’t hesitate to contact us at <a href="mailto:lfs-johsc@lists.ubc.ca">lfs-johsc@lists.ubc.ca</a>.
    </p>
    '''


def send_info_email(user):
    """ Send an email when adding a user to a lab and creating new users """

    title = 'You are added to LFS TRMS'

    message = '''\
    <div>
        <p>Hi {0} {1},</p>
        <div>You have recently been added to the LFS Training Record Management System. Please visit <a href={3}>{3}</a> to upload your training records. Thank you.</div>
        <br />
        <div>
            <b>Please note that if you try to access the LFS Training Record Management System off campus,
            you must be connected via
            <a href="https://it.ubc.ca/services/email-voice-internet/myvpn">UBC VPN</a>.</b>
        </div>
        <br />
        <div>{2}</div>
        <br />
        <p>Best regards,</p>
        <p>LFS Training Record Management System</p>
    </div>
    '''.format(user.first_name, user.last_name, welcome_message(), settings.SITE_URL)

    sent = send_mail(title, message, settings.EMAIL_FROM, [ user.email ], fail_silently=False, html_message=message)
    if not sent:
        sent.error = 'Django send_mail went wrong'
    return sent




def add_next_str_to_session(request, curr_user):
    if request.user.id != curr_user.id and request.GET.get('next'):
        next = request.get_full_path().split('next=')
        request.session['next'] = next[1]

    viewing = {}
    if request.user.id != curr_user.id and request.session.get('next'):
        viewing = get_viewing(request.session.get('next'))
    return viewing


def get_viewing(next):
    """ Get viewing information for going back to the previous page """

    split_query = next.split('?')
    res = resolve(split_query[0])

    viewing = {}
    if res.url_name == 'all_users' or res.url_name == 'api_updates':
        query = ''
        if len(split_query) > 1: 
            query = split_query[1]
        
        viewing = { 
            'page': res.url_name, 
            'query': query,
            'name': make_capital(res.url_name),
            'route': os.path.join(settings.SITE_URL, res.route)
        }

    elif res.url_name == 'area_details':
        id = res.kwargs['area_id']
        viewing = { 
            'page': 'area_details', 
            'id': id, 
            'name': get_lab_by_id(id).name 
        }

    return viewing


# Helper functions

def get_error_messages(errors):
    """ Get error messages """

    messages = ''
    for key in errors.keys():
        print(key)
        value = errors[key]
        if key == '__all__':
            messages += value[0]['message'] + ' '
        else:
            messages += '<strong>' + key.replace('_', ' ').upper() + ':</strong> ' + value[0]['message'] + ' '
    return messages.strip()

def make_capital(name):
    sp = name.split('_')
    first = sp[0].capitalize()
    second = sp[1].capitalize()
    if first == 'Api':
        first = 'API'

    return '{0} {1}'.format(first, second)
    

def convert_date_to_str(date):
    return date.strftime('%Y-%m-%d')

"""def get_expiry_date(completion_date, cert):
    expiry_year = completion_date.year + int(cert.expiry_in_years)
    return date(year=expiry_year, month=completion_date.month, day=completion_date.day)"""