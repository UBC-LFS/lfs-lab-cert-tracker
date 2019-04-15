from datetime import datetime

from django.contrib.auth.hashers import make_password

from django.forms.models import model_to_dict

from django.contrib.auth.models import User as AuthUser
from lfs_lab_cert_tracker.models import User, Lab, Cert, LabCert, UserCert, UserLab

"""
Provides an API to the Django ORM for any queries that are required
"""

# User CRUD
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist as dne:
        return None

def get_user_by_cwl(cwl):
    return User.objects.get(cwl=cwl)

def get_users(n=None):
    return [model_to_dict(user) for user in User.objects.all()]

def delete_user(user_id):
    AuthUser.objects.get(id=user_id).delete()
    User.objects.get(id=user_id).delete()
    return {'user_id': user_id}

# Cert CRUD
def get_certs(n=None):
    return [model_to_dict(cert) for cert in Cert.objects.all()]

def create_cert(name):
    cert = Cert.objects.create(name=name)
    return model_to_dict(cert)

def delete_cert(cert_id):
    Cert.objects.get(id=cert_id).delete()
    return {'cert_id': cert_id}

# Lab CRUD
def get_lab(lab_id):
    return Lab.objects.get(id=lab_id)

def get_labs(n=None):
    return [model_to_dict(lab) for lab in Lab.objects.all()]

def create_lab(name):
    lab = Lab.objects.create(name=name)
    return model_to_dict(lab)

def delete_lab(lab_id):
    Lab.objects.get(id=lab_id).delete()
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

def update_or_create_user_cert(user_id, cert_id, cert_file, expiry_date):
    user_cert, created = UserCert.objects.get_or_create(user_id=user_id, cert_id=cert_id, defaults={'cert_file': cert_file, 'status': UserCert.PENDING, 'uploaded_date': datetime.now(), 'expiry_date': expiry_date})
    if not created:
        user_cert.uploaded_date = datetime.now()
        user_cert.cert_file = cert_file
        user_cert.expiry_date = expiry_date
        user_cert.save()
    return model_to_dict(user_cert)

def delete_user_cert(user_id, cert_id):
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
    return cert.expiry_date is not None and now > cert.expiry_date

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
    user_lab = UserLab.objects.create(user_id=user_id, lab_id=lab_id, role=role)
    return model_to_dict(user_lab)

def delete_user_lab(user_id, lab_id):
    UserLab.objects.get(user=user_id, lab=lab_id).delete()
    return {'user_id': user_id, 'lab_id': lab_id}

# LabCert CRUD
def get_lab_certs(lab_id, n=None):
    lab_certs = LabCert.objects.filter(lab=lab_id).prefetch_related('cert')
    return [model_to_dict(lab_cert.cert) for lab_cert in lab_certs]

def create_lab_cert(lab_id, cert_id):
    lab_cert = LabCert.objects.create(lab_id=lab_id, cert_id=cert_id)
    return model_to_dict(lab_cert)

def delete_lab_cert(lab_id, cert_id):
    LabCert.objects.get(lab=lab_id, cert=cert_id).delete()
    return {'lab_id': lab_id, 'cert_id': cert_id}

# User CRUD
def create_user(first_name, last_name, email, cwl):
    # TODO: Replace the need to create an AuthUser with a password
    auth_user = AuthUser.objects.create(
        username=cwl,
        email=email,
        password=make_password('foobar'),
    )

    user = User.objects.create(
        id=auth_user.id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        cwl=cwl
    )

    return model_to_dict(user)
