from datetime import datetime, timedelta
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from django.forms.models import model_to_dict

from django.contrib.auth.models import User as AuthUser
from lfs_lab_cert_tracker.models import Lab, Cert, LabCert, UserCert, UserLab, UserInactive


"""
Provides an API to the Django ORM for any queries that are required
"""

# User CRUD
def get_user(user_id):
    try:
        return AuthUser.objects.get(id=user_id)
    except AuthUser.DoesNotExist as dne:
        return None

def get_user_by_username(username):
    try:
        return AuthUser.objects.get(username=username)
    except AuthUser.DoesNotExist as dne:
        return None

def get_users(n=None):
    user_inactives = [ model_to_dict(user_inactive) for user_inactive in UserInactive.objects.all() ]
    #print(user_inactives)
    users = []
    for user in AuthUser.objects.all().order_by('id'):
        user_dict = model_to_dict(user)
        for user_inactive in user_inactives:
            #print(user_inactive['user'])
            if user.id == user_inactive['user']:
                #print(user.id, user_inactive['inactive_date'])
                user_dict['inactive_date'] = user_inactive['inactive_date']
        users.append(user_dict)

    #print(users)
    return users
    #return [model_to_dict(user) for user in AuthUser.objects.all().order_by('id')]

def delete_user(user_id):
    AuthUser.objects.get(id=user_id).delete()
    return {'user_id': user_id}

def switch_admin(user_id):
    user = AuthUser.objects.get(id=user_id)
    user.is_superuser = not user.is_superuser
    user.save(update_fields=['is_superuser'])
    return model_to_dict(user)

def switch_inactive(user_id):
    user = AuthUser.objects.get(id=user_id)
    if user.is_active:
        UserInactive.objects.create(user_id=user_id, inactive_date=datetime.now())
    else:
        UserInactive.objects.get(user_id=user_id).delete()
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    return model_to_dict(user)

# Cert CRUD
def get_certs(n=None):
    return [model_to_dict(cert) for cert in Cert.objects.all().order_by('id')]

def create_cert(name, expiry_in_years):
    cert, created = Cert.objects.get_or_create(name=name, expiry_in_years=expiry_in_years)
    if created:
        return model_to_dict(cert)
    else:
        return None

def delete_cert(cert_id):
    Cert.objects.get(id=cert_id).delete()
    return {'cert_id': cert_id}

def get_cert(cert_id):
    cert = Cert.objects.get(id=cert_id)
    return model_to_dict(cert)

# Lab CRUD
def get_lab(lab_id):
    lab = Lab.objects.get(id=lab_id)
    return model_to_dict(lab)

def get_labs(n=None):
    return [model_to_dict(lab) for lab in Lab.objects.all().order_by('id')]

def create_lab(name):
    lab = Lab.objects.create(name=name)
    return model_to_dict(lab)

def delete_lab(lab_id):
    Lab.objects.get(id=lab_id).delete()
    return {'lab_id': lab_id}

def update_lab(lab_id, name):
    #print(lab_id, name)
    lab = Lab.objects.get(id=lab_id)
    lab.name = name
    lab.save(update_fields=['name'])
    return {'lab_id': lab_id}


# UserCert CRUD
def get_user_certs(user_id):
    user_certs = UserCert.objects.filter(user_id=user_id).prefetch_related('cert')
    res = []
    for user_cert in user_certs:
        dict_user_cert = model_to_dict(user_cert)
        dict_user_cert.update(model_to_dict(user_cert.cert))
        res.append(dict_user_cert)
    return res

def get_user_cert(user_id, cert_id):
    user_cert = UserCert.objects.filter(user=user_id, cert=cert_id).prefetch_related('cert')[0]
    res = model_to_dict(user_cert)
    res.update(model_to_dict(user_cert.cert))
    return res

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

def delete_user_cert(user_id, cert_id):
    UserCert.objects.get(user_id=user_id, cert_id=cert_id).delete()
    return {'user_id': user_id, 'cert_id': cert_id}

def update_user_cert(user_id, cert_id):
    UserCert.objects.get(user_id=user_id, cert_id=cert_id).delete()
    return {'user_id': user_id, 'cert_id': cert_id}


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

    for uc in user_certs:
        if uc.cert.id in required_cert_ids and is_user_cert_expired(uc):
            missing.append(uc.cert)

    return [model_to_dict(m) for m in missing]

def create_user_lab(user_id, lab_id, role):
    user_lab, created  = UserLab.objects.get_or_create(user_id=user_id, lab_id=lab_id, role=role)
    if created:
        return model_to_dict(user_lab)
    else:
        return None

def delete_user_lab(user_id, lab_id):
    UserLab.objects.get(user=user_id, lab=lab_id).delete()
    return {'user_id': user_id, 'lab_id': lab_id}

# LabCert CRUD
def get_lab_certs(lab_id, n=None):
    lab_certs = LabCert.objects.filter(lab=lab_id).prefetch_related('cert')
    return [model_to_dict(lab_cert.cert) for lab_cert in lab_certs]

def create_lab_cert(lab_id, cert_id):
    lab_cert, created = LabCert.objects.get_or_create(lab_id=lab_id, cert_id=cert_id)
    if created:
        return model_to_dict(lab_cert)
    else:
        return None

def delete_lab_cert(lab_id, cert_id):
    LabCert.objects.get(lab=lab_id, cert=cert_id).delete()
    return {'lab_id': lab_id, 'cert_id': cert_id}

# User CRUD
def create_user(first_name, last_name, email, username):
    user = get_user_by_username(username)
    print('user ', user)
    if user:
        return None
    # TODO: Replace the need to create an AuthUser with a password
    user_created = AuthUser.objects.create(
        first_name=first_name,
        last_name=last_name,
        username=username,
        email=email,
        password=make_password(''),
    )
    print( "user_created ", user_created )
    return model_to_dict(user_created)
