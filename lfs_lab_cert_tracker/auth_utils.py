from django.core.exceptions import PermissionDenied
from django.http import (HttpResponse, HttpResponseForbidden, HttpResponseRedirect, HttpResponseServerError)
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.models import User
from django.shortcuts import render
from django.shortcuts import get_object_or_404

from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from lfs_lab_cert_tracker.models import UserLab

"""
Utility functions for authentication, mainly for checking that a user has correct permissions
"""

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

def get_user_or_404(user_id):
    return get_object_or_404(User, id=user_id)

def admin_or_pi_only(func):
    def admin_or_pi_only(request, *args, **kwargs):
        if is_admin(request.user) or is_principal_investigator(request.user.id, kwargs['lab_id']):
            return func(request, *args, **kwargs)
        else:
            raise PermissionDenied
    return admin_or_pi_only

def admin_or_pi_or_user(func):
    def admin_or_pi_or_user(request, *args, **kwargs):
        get_user_or_404(kwargs['user_id'])
        if request.user.id == kwargs['user_id'] or is_admin(request.user) == True or kwargs['user_id'] in get_lab_users_involved_in_lab_by_pi(request.user.id):
            return func(request, *args, **kwargs)
        else:
            raise PermissionDenied
    return admin_or_pi_or_user

def get_lab_users_involved_in_lab_by_pi(loggedin_user_id):
    ''' Get labs that an user gets involved '''
    users = set()

    userlabs = UserLab.objects.filter(user=loggedin_user_id, role=UserLab.PRINCIPAL_INVESTIGATOR)
    if userlabs.exists():
        for userlab in userlabs:
            labs = UserLab.objects.filter(lab=userlab.lab.id)
            if labs.exists():
                for lab in labs:
                    users.add(lab.user.id)

    return list(users)
