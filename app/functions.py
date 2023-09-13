from django.shortcuts import get_object_or_404

from django.contrib.auth.models import User
from lfs_lab_cert_tracker.models import *

from datetime import datetime, date


# User
def get_users(option=None):
    """ Get all users """
    if option == 'active':
        return User.objects.filter(is_active=True).order_by('last_name', 'first_name')
    return User.objects.all().order_by('last_name', 'first_name')

def get_user_by_username(username):
    user = User.objects.filter(username=username)
    return user.first() if user.exists() else None



def get_user_certs(user):
    return user.usercert_set.all().distinct('cert__name')

def get_user_missing_certs(user_id):
    required_certs = Cert.objects.filter(labcert__lab__userlab__user_id=user_id).distinct()
    certs = Cert.objects.filter(usercert__user_id=user_id).distinct()
    return required_certs.difference(certs).order_by('name')

def get_user_expired_certs(user_id):
    return Cert.objects.filter( Q(usercert__user_id=user_id) & Q(usercert__expiry_date__lt=date.today()) & ~Q(usercert__completion_date=F('usercert__expiry_date')) ).distinct()



# Cert

def get_certs():
    return Cert.objects.all()

"""def get_cert_by_id(cert_id):
    cert = Cert.objects.filter(id=cert_id)
    return cert.first() if cert.exists() else None

def get_cert_by_id_404(cert_id):
    return get_object_or_404(Cert, id=cert_id)

def get_cert_by_name(cert_name):
    cert = Cert.objects.filter(name=cert_name)
    return cert.first() if cert.exists() else None"""


# Helper functions

def get_expiry_date(completion_date, cert):
    #print('get_expiry_date', completion_date, cert.expiry_in_years)
    expiry_year = completion_date.year + int(cert.expiry_in_years)
    return date(year=expiry_year, month=completion_date.month, day=completion_date.day)