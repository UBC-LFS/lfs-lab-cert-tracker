import os
from django.conf import settings
from datetime import datetime, timedelta
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from django.forms.models import model_to_dict
from django.http import Http404

from django.contrib.auth.models import User as AuthUser
from lfs_lab_cert_tracker.models import *


"""
Provides an API to the Django ORM for any queries that are required
"""

# User

def get_user_404(user_id):
    ''' Get an user or 404 '''

    return get_object_or_404(AuthUser, id=user_id)

def get_users_order_by_name():
    ''' Get all users ordered by a full name '''

    return AuthUser.objects.all().order_by('last_name', 'first_name')


# Area

def get_area_404(area_id):
    ''' Get an user or 404 '''
    return get_object_or_404(Lab, id=area_id)

def get_areas():
    ''' Get all areas '''
    return Lab.objects.all().order_by('name')


# User Training


# User lab


def add_users_to_areas(areas):
    ''' Add user info to areas '''

    for area in areas:
        area.has_lab_users = []
        area.has_pis = []
        for userlab in area.userlab_set.all():
            if userlab.role == UserLab.LAB_USER:
                area.has_lab_users.append(userlab.user.id)
            elif userlab.role == UserLab.PRINCIPAL_INVESTIGATOR:
                area.has_pis.append(userlab.user.id)

    return areas





#------------------


def get_users():
    """ Get all users """

    user_inactives = [ model_to_dict(user_inactive) for user_inactive in UserInactive.objects.all() ]
    users = []
    for user in AuthUser.objects.all().order_by('id'):
        user_dict = model_to_dict(user)
        for user_inactive in user_inactives:
            if user.id == user_inactive['user']:
                user_dict['inactive_date'] = user_inactive['inactive_date']
        users.append(user_dict)

    return users



def add_missing_certs(users):
    ''' Add missing certs into users '''
    for user in users:
        certs = get_missing_certs_query_object(user.id)
        if len(certs) > 0:
            user.missing_certs = certs
        else:
            user.missing_certs = None
    return users




def get_user_by_username(username):
    """ Find a user by username """
    try:
        return AuthUser.objects.get(username=username)
    except AuthUser.DoesNotExist as dne:
        return None





def switch_inactive(user_id):
    """ Switch a user to Active or Inactive """

    try:
        user = AuthUser.objects.get(id=user_id)
        if user.is_active:
            UserInactive.objects.create(user_id=user_id, inactive_date=datetime.now())
        else:
            UserInactive.objects.get(user_id=user_id).delete()
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        return model_to_dict(user)
    except AuthUser.DoesNotExist:
        return None


# Lab CRUD


def get_lab(lab_id):
    """ Find a lab by id """

    try:
        lab = Lab.objects.get(id=lab_id)
        return lab
    except Lab.DoesNotExist:
        return None





# Cert CRUD
def get_certs():
    """ Get all certificates """

    return [model_to_dict(cert) for cert in Cert.objects.all()]

def get_cert(cert_id):
    """ Find a certificate by id """

    try:
        cert = Cert.objects.get(id=cert_id)
        return model_to_dict(cert)
    except Cert.DoesNotExist:
        return None

def get_cert_404(cert_id):
    ''' Get a cert '''
    return get_object_or_404(Cert, id=cert_id)


def delete_cert(cert_id):
    """ Delete a certificate """
    try:
        Cert.objects.get(id=cert_id).delete()
        return {'cert_id': cert_id}
    except:
        return None


# UserCert CRUD

def get_user_certs_404(user_id):
    ''' Get all certs of an user '''
    user = get_user_404(user_id)
    return user.usercert_set.all()

def get_user_cert_404(user_id, cert_id):
    ''' Get a cert of an user '''
    user = get_user_404(user_id)
    uc = user.usercert_set.filter(cert_id=cert_id)
    if uc.exists():
        return uc.first()
    raise Http404



def all_certs_expired_in_30days():
    min_date = datetime.now()
    max_date = datetime.now() + timedelta(days=30)
    certs = UserCert.objects.filter(expiry_date__gte=min_date).order_by('expiry_date')
    return certs.filter(expiry_date__lte=max_date)


# UserCert CRUD
def get_missing_certs(user_id):
    # Get the labs that the user is signed up for
    user_lab_ids = UserLab.objects.filter(user_id=user_id).values_list('lab_id')
    lab_certs = LabCert.objects.filter(lab_id__in=user_lab_ids).distinct('cert').prefetch_related('cert')

    # From these labs determine which certs are missing or expired
    user_cert_ids = UserCert.objects.filter(user_id=user_id).values_list('cert_id')
    missing_user_certs = lab_certs.exclude(cert_id__in=user_cert_ids)

    return [model_to_dict(missing_user_cert.cert) for missing_user_cert in missing_user_certs]


def get_missing_certs_query_object(user_id):
    user_lab_ids = UserLab.objects.filter(user_id=user_id).values_list('lab_id')
    lab_certs = LabCert.objects.filter(lab_id__in=user_lab_ids).distinct('cert').prefetch_related('cert')

    # From these labs determine which certs are missing or expired
    user_cert_ids = UserCert.objects.filter(user_id=user_id).values_list('cert_id')

    return lab_certs.exclude(cert_id__in=user_cert_ids)

def get_expired_certs(user_id):
    user_certs = UserCert.objects.filter(user_id=user_id).prefetch_related('cert')
    expired_user_certs = []
    now = datetime.now()
    for uc in user_certs:
        if is_user_cert_expired(uc):
            expired_user_certs.append(uc)
    return [model_to_dict(uc.cert) for uc in expired_user_certs]

def update_or_create_user_cert(user_id, cert_id, cert_file, completion_date, expiry_date):
    user_cert, created = UserCert.objects.get_or_create(
        user_id=user_id,
        cert_id=cert_id,
        defaults={
            'cert_file': cert_file,
            'uploaded_date': datetime.now(),
            'completion_date': completion_date,
            'expiry_date': expiry_date
        }
    )
    if not created:
        user_cert.cert_file = cert_file
        user_cert.uploaded_date = datetime.now()
        user_cert.completion_date = completion_date
        user_cert.expiry_date = expiry_date
        user_cert.save()

    return model_to_dict(user_cert)



# UserLab CRUD
def get_user_labs(user_id, is_principal_investigator=None):
    if is_principal_investigator:
        user_labs = UserLab.objects.filter(user=user_id, role=UserLab.PRINCIPAL_INVESTIGATOR)
    else:
        user_labs = UserLab.objects.filter(user=user_id)
    return [model_to_dict(user_lab.lab) for user_lab in user_labs]


def get_users_in_lab(lab_id):
    users_in_lab = UserLab.objects.filter(lab=lab_id).prefetch_related('user')
    return [model_to_dict(user_in_lab.user) for user_in_lab in users_in_lab]

def get_users_missing_certs(lab_id):
    """
    Given a lab returns users that are missing certs and the certs they are missing
    """
    lab_users = UserLab.objects.filter(lab=lab_id).prefetch_related('user')

    users_missing_certs = []
    for lab_user in lab_users:
        missing_lab_certs = get_missing_lab_certs(lab_user.user_id, lab_id)
        if missing_lab_certs:
            users_missing_certs.append((lab_user, missing_lab_certs))

    return [(model_to_dict(user_missing_certs.user), missing_lab_cert) for user_missing_certs, missing_lab_cert in users_missing_certs]

def get_users_expired_certs(lab_id):
    lab_users = UserLab.objects.filter(lab=lab_id).prefetch_related('user')

    users_expired_certs = []
    for lab_user in lab_users:
        user_certs = UserCert.objects.filter(user=lab_user.user_id).prefetch_related('cert')
        required_certs = LabCert.objects.filter(lab=lab_id).prefetch_related('cert')

        user_cert_ids = set(user_certs.values_list('cert_id', flat=True))
        required_cert_ids = set(required_certs.values_list('cert_id', flat=True))

        expired_certs = []
        for uc in user_certs:
            if uc.cert.id in required_cert_ids and is_user_cert_expired(uc):
                expired_certs.append(uc.cert)

        if len(expired_certs) > 0:
            users_expired_certs.append({
                'user': lab_user.user,
                'expired_certs': expired_certs
            })

    return users_expired_certs


def is_user_cert_expired(cert):
    now = datetime.now().date()
    return cert.expiry_date is not None and now > cert.expiry_date and cert.expiry_date != cert.completion_date

def get_missing_lab_certs(user_id, lab_id):
    user_certs = UserCert.objects.filter(user=user_id).prefetch_related('cert')
    required_certs = LabCert.objects.filter(lab=lab_id).prefetch_related('cert')

    user_cert_ids = set(user_certs.values_list('cert_id', flat=True))
    required_cert_ids = set(required_certs.values_list('cert_id', flat=True))

    missing = []
    for rc in required_certs:
        if rc.cert.id not in user_cert_ids:
            missing.append(rc.cert)

    #for uc in user_certs:
    #    if uc.cert.id in required_cert_ids and is_user_cert_expired(uc):
    #        expiried.append(uc.cert)

    return [model_to_dict(m) for m in missing]

def add_users_to_labs(user_id, lab_id, role):
    """ Add a user to a lab """

    try:
        has_existed = UserLab.objects.get(user_id=user_id, lab_id=lab_id)
    except UserLab.DoesNotExist:
        has_existed = None

    if has_existed:
        return None

    user_lab = UserLab.objects.create(user_id=user_id, lab_id=lab_id, role=role)
    return model_to_dict(user_lab)







# LabCert CRUD




# Helper methods



def validate_parameters(request, params):
    ''' Validate request parameters '''
    for param in params:
        if request.GET.get(param) == None: raise Http404
    return True

def validate_url_tab(request, path):
    ''' Validate a tab name in url '''
    if request.GET.get('t') not in path:
        raise Http404

def can_req_parameters_access(request, params):
    ''' Check whether request parameters are valid or not '''
    if validate_parameters(request, params):
        validate_url_tab(request, ['all', 'report', 'new'])



# for testing

def get_error_messages(errors):
    messages = ''
    for key in errors.keys():
        value = errors[key]
        messages += key.replace('_', ' ').upper() + ': ' + value[0]['message'] + ' '
    return messages.strip()

def switch_admin(user_id):
    """ Switch a user to Admin or not Admin """

    try:
        user = AuthUser.objects.get(id=user_id)
        user.is_superuser = not user.is_superuser
        user.save(update_fields=['is_superuser'])
        return model_to_dict(user)
    except AuthUser.DoesNotExist:
        return None

def delete_user(user_id):
    """ Delete a user """
    try:
        user = AuthUser.objects.get(id=user_id)
        user.delete()
        return {'user_id': user_id}
    except AuthUser.DoesNotExist:
        return None

def get_user(user_id):
    """ Find a user by id"""
    try:
        return AuthUser.objects.get(id=user_id)
    except AuthUser.DoesNotExist as dne:
        return None

def get_user_cert(user_id, cert_id):
    user_cert_query_set = UserCert.objects.filter(user=user_id, cert=cert_id).prefetch_related('cert')
    if user_cert_query_set.count() > 0:
        user_cert = user_cert_query_set[0]
        res = model_to_dict(user_cert)
        res.update(model_to_dict(user_cert.cert))
        return res
    else:
        return None

def get_user_certs(user_id):
    user_certs = UserCert.objects.filter(user_id=user_id).prefetch_related('cert')
    res = []
    for user_cert in user_certs:
        dict_user_cert = model_to_dict(user_cert)
        dict_user_cert.update(model_to_dict(user_cert.cert))
        res.append(dict_user_cert)
    return res


def delete_user_cert(user_id, cert_id):
    UserCert.objects.get(user_id=user_id, cert_id=cert_id).delete()
    os.rmdir( os.path.join( settings.MEDIA_ROOT, 'users', str(user_id), 'certificates', str(cert_id) ) )
    return {'user_id': user_id, 'cert_id': cert_id}


"""
def update_user_cert(user_id, cert_id):
    UserCert.objects.get(user_id=user_id, cert_id=cert_id).delete()
    return {'user_id': user_id, 'cert_id': cert_id}
"""


def delete_all_areas_in_user(data):
    ''' Delete all areas in an user '''

    user = get_user_404( data.get('user') )
    all_userlab = user.userlab_set.all()

    if len(all_userlab) > 0:
        return user.userlab_set.all().delete()

    return None

def update_or_create_areas_to_user(data):
    ''' update or create areas to an user '''

    areas = data.getlist('areas[]')
    user = get_user_404( data.get('user') )
    all_userlab = user.userlab_set.all()

    report = { 'updated': [], 'created': [], 'deleted': [] }
    used_areas = []
    for area in areas:
        splitted = area.split(',')
        lab = get_area_404(splitted[0])
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


def delete_lab(lab_id):
    """ Delete a lab """

    try:
        Lab.objects.get(id=lab_id).delete()
        return {'lab_id': lab_id}
    except Lab.DoesNotExist:
        return None


def get_labs():
    """ Get all labs """

    return [model_to_dict(lab) for lab in Lab.objects.all()]


def get_lab_certs(lab_id, n=None):
    """ Get all certificates in a lab """

    lab_certs = LabCert.objects.filter(lab=lab_id).prefetch_related('cert')
    return [model_to_dict(lab_cert.cert) for lab_cert in lab_certs]

def delete_lab_cert(lab_id, cert_id):
    """ Delete a certificate in a lab """

    LabCert.objects.get(lab=lab_id, cert=cert_id).delete()
    return {'lab_id': lab_id, 'cert_id': cert_id}


def create_lab_cert(lab_id, cert_id):
    """ Add a certificate to a lab """

    lab_cert, created = LabCert.objects.get_or_create(lab_id=lab_id, cert_id=cert_id)
    if created:
        return model_to_dict(lab_cert)
    else:
        return None


def create_user_lab(user_id, lab_id, role):
    """ Add a user to a lab """

    try:
        has_existed = UserLab.objects.get(user_id=user_id, lab_id=lab_id)
    except UserLab.DoesNotExist:
        has_existed = None

    if has_existed:
        return None

    user_lab = UserLab.objects.create(user_id=user_id, lab_id=lab_id, role=role)
    return model_to_dict(user_lab)


def switch_lab_role(user_id, lab_id):
    role = None
    try:
        user_lab = UserLab.objects.get(user=user_id, lab=lab_id)
        if user_lab.role == UserLab.LAB_USER:
            user_lab.role = UserLab.PRINCIPAL_INVESTIGATOR
            role = 'Supervisor'
        else:
            user_lab.role = UserLab.LAB_USER
            role = 'User'
        user_lab.save(update_fields=['role'])
        return {'user_id': user_id, 'lab_id': lab_id, 'role': role}
    except UserLab.DoesNotExist:
        return None

def delete_user_lab(user_id, lab_id):
    """ Delete a user in a lab """

    UserLab.objects.get(user=user_id, lab=lab_id).delete()
    return {'user_id': user_id, 'lab_id': lab_id}


def can_user_delete(user, user_id):
    ''' Check whether an user can delete a cert or not '''
    return user.id == user_id or user.is_superuser

def delete_user_cert_404(user_id, cert_id):
    ''' Delete a cert of an user '''
    user = get_user_404(user_id)
    user_cert = user.usercert_set.filter(cert_id=cert_id)
    uc = None
    if user_cert.exists():
        uc = user_cert.first()
        user_cert.delete()

        dirpath = os.path.join( settings.MEDIA_ROOT, 'users', str(user_id), 'certificates', str(cert_id) )
        if os.path.exists(dirpath) and os.path.isdir(dirpath):
            os.rmdir(dirpath)

    return uc if uc else False
