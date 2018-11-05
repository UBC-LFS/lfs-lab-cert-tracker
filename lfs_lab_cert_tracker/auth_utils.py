from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from lfs_lab_cert_tracker.models import UserLab

def is_admin(user):
    return user.groups.filter(name='admin').exists()

def is_principal_investigator(user_id, lab_id):
    return UserLab.objects.filter(user=user_id, lab=lab_id, role=UserLab.PRINCIPAL_INVESTIGATOR).exists()

def user_or_admin(func):
    def user_or_admin(request, *args, **kwargs):
        if is_admin(request.user) or request.user.id == kwargs.get('user_id', None):
            return func(request, *args, **kwargs)
        else:
            raise PermissionDenied
    return user_or_admin
