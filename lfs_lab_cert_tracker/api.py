from django.contrib.auth.hashers import make_password

from django.forms.models import model_to_dict

from django.contrib.auth.models import User as AuthUser
from lfs_lab_cert_tracker.models import User, Lab, Cert, LabCert, UserCert, UserLab

# User CRUD
def get_users(n=None):
    return [model_to_dict(user) for user in User.objects.all()]

# Cert CRUD
def get_certs(n=None):
    return [model_to_dict(cert) for cert in Cert.objects.all()]

def create_cert(name):
    cert = Cert.objects.create(name=name)
    return model_to_dict(cert)

def delete_cert(cert_id):
    try:
        Cert.objects.delete(id=cert_id)
        return True
    except:
        return False

# Lab CRUD
def get_labs(n=None):
    return [model_to_dict(lab) for lab in Lab.objects.all()]

def create_lab(name):
    lab = Lab.objects.create(name=name)
    return model_to_dict(lab)

def delete_lab(lab_id):
    try:
        Lab.objects.delete(id=lab_id)
        return True
    except:
        return False

# UserCert CRUD
def get_user_certs(user_id, n=None):
    user_certs = UserCert.objects.filter(user_id=user_id)
    return [model_to_dict(user_cert) for user_cert in user_certs]

def create_user_cert(user_id, cert_id):
    user_cert = UserCert.objects.create(user=user_id, cert=cert_id)
    return model_to_dict(user_cert)

def delete_user_cert(user_id, cert_id):
    user_cert = UserCert.objects.delete(user=user_id, cert=cert_id)
    return model_to_dict(user_cert)

# UserLab CRUD
def get_user_labs(user_id, n=None):
    user_labs = UserLab.objects.filter(user=user_id)
    return [model_to_dict(user_lab.lab) for user_lab in user_labs]

def create_user_lab(user_id, lab_id, role):
    user = User.objects.get(id=user_id)
    lab = Lab.objects.get(id=lab_id)
    user_lab = UserLab.objects.create(user_id=user, lab_id=lab, role=role)
    return model_to_dict(user_lab)

def delete_user_lab(user_id, lab_id):
    user_lab = UserLab.objects.delete(user=user_id, lab=lab_id)
    return model_to_dict(user_lab)

# LabCert CRUD
def get_lab_certs(lab_id, n=None):
    lab_certs = LabCert.objects.filter(lab=lab_id)
    return [model_to_dict(lab_cert) for lab_cert in lab_certs]

def create_lab_cert(lab_id, cert_id):
    lab_cert = LabCert.objects.create(lab=lab_id, cert=cert_id)
    return model_to_dict(lab_cert)

def delete_lab_cert(lab_id, cert_id):
    lab_cert = LabCert.objects.delete(lab=lab_id, cert=cert_id)
    return model_to_dict(lab_cert)

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
