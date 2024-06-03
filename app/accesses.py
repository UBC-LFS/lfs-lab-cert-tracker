from django.core.exceptions import PermissionDenied

from .functions import *

def access_admin_only(view_func):
    """ Access an admin only """

    def wrap(request, *args, **kwargs):
        if request.user.is_superuser is True:
            return view_func(request, *args, **kwargs)
        else:
            raise PermissionDenied
    return wrap


def access_pi_admin(view_func):
    """
    Access for an admin and PI in the area
    Usage: used in AreaDetailsView
    """

    def wrap(request, *args, **kwargs):
        if request.user.is_superuser or is_pi_in_area(request.user.id, kwargs['area_id']):
            return view_func(request, *args, **kwargs)
        else:
            raise PermissionDenied

    return wrap


def access_loggedin_user_pi_admin(view_func):
    """
    Access for a loggedin user and a PI in the area and an admin
    Usage: used in UserDetailsView
    """

    def wrap(request, *args, **kwargs):
        user_id = kwargs['user_id']
        if request.user.id == user_id or request.user.is_superuser or user_id in get_users_in_area_by_pi(request.user.id):
            return view_func(request, *args, **kwargs)
        else:
            raise PermissionDenied

    return wrap


def access_all(view_func):
    """ Access for all users authenticated """

    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated != True:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrap


def access_loggedin_user_admin(view_func):
    """ Access for a logged-in user or an admin """

    def wrap(request, *args, **kwargs):
        if request.user.is_superuser is True or request.user.id == kwargs['user_id']:
            return view_func(request, *args, **kwargs)
        else:
            raise PermissionDenied
    return wrap

def access_loggedin_user_only(view_func):
    """ Access for a logged-in user only """

    def wrap(request, *args, **kwargs):
        if request.user.id == kwargs['user_id']:
            return view_func(request, *args, **kwargs)
        else:
            raise PermissionDenied
    return wrap
