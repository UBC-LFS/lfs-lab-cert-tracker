from django.forms.models import model_to_dict

from lfs_lab_cert_tracker.models import Cert, LabCert

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

def get_lab_certs(n=None):
    return [model_to_dict(lab_cert) for lab_cert in LabCert.objects.all()]

def create_lab_cert(lab_id, cert_id):
    lab_cert = LabCert.objects.create(lab=lab, cert=cert)
    return model_to_dict(lab_cert)

def delete_lab_cert(lab_id, cert_id):
    lab_cert = LabCert.objects.delete(lab=lab, cert=cert)
    return model_to_dict(lab_cert)
