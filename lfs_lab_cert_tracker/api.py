from django.forms.models import model_to_dict

from django.contrib.auth.models import User
from lfs_lab_cert_tracker.models import Lab, Cert, LabCert, UserCert, UserLab

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
    user_cert = UserCert.objects.create(user_id=user_id, cert_id=cert_id)
    return model_to_dict(user_cert)

def delete_user_cert(user_id, cert_id):
    user_cert = UserCert.objects.delete(user_id=user_id, cert_id=cert_id)
    return model_to_dict(user_cert)

# UserLab CRUD
def get_user_labs(user_id, n=None):
    user_labs = UserLab.objects.filter(user_id=user_id)
    return [model_to_dict(user_lab) for user_lab in user_labs]

def create_user_lab(user_id, lab_id):
    user_lab = UserLab.objects.create(user_id=user_id, lab_id=lab_id)
    return model_to_dict(user_lab)

def delete_user_lab(user_id, lab_id):
    user_lab = UserLab.objects.delete(user_id=user_id, lab_id=lab_id)
    return model_to_dict(user_lab)

# LabCert CRUD
def get_lab_certs(lab_id, n=None):
    lab_certs = LabCert.objects.filter(lab_id=lab_id)
    return [model_to_dict(lab_cert) for lab_cert in lab_certs]

def create_lab_cert(lab_id, cert_id):
    lab_cert = LabCert.objects.create(lab_id=lab_id, cert_id=cert_id)
    return model_to_dict(lab_cert)

def delete_lab_cert(lab_id, cert_id):
    lab_cert = LabCert.objects.delete(lab_id=lab_id, cert_id=cert_id)
    return model_to_dict(lab_cert)
