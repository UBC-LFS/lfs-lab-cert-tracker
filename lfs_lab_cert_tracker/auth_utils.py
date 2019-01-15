from django.core.exceptions import PermissionDenied
from django.http import (HttpResponse, HttpResponseForbidden, HttpResponseRedirect, HttpResponseServerError)
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.models import User
from django.shortcuts import render

from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from lfs_lab_cert_tracker.models import UserLab

def is_admin(user):
    return user.is_superuser

def is_principal_investigator(user_id, lab_id):
    return UserLab.objects.filter(user=user_id, lab=lab_id, role=UserLab.PRINCIPAL_INVESTIGATOR).exists()

def user_or_admin(func):
    def user_or_admin(request, *args, **kwargs):
        if is_admin(request.user) or request.user.id == kwargs.get('user_id', None):
            return func(request, *args, **kwargs)
        else:
            raise PermissionDenied
    return user_or_admin

def admin_only(func):
    def admin_only(request, *args, **kwargs):
        if is_admin(request.user):
            return func(request, *args, **kwargs)
        else:
            raise PermissionDenied
    return admin_only

def get_user(username):
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None
