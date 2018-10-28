from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.shortcuts import render
from django.http import HttpResponseForbidden

from lfs_lab_cert_tracker import api
from lfs_lab_cert_tracker import auth_utils
from lfs_lab_cert_tracker.forms import (LabForm, CertForm, UserForm,
        UserLabForm, LabCertForm, UserCertForm)

"""
HTTP endpoints to transfer HTML
"""

@login_required
@require_http_methods(['GET'])
def index(request):
    is_admin = auth_utils.is_admin(request.user)
    return render(request,
            'lfs_lab_cert_tracker/index.html',
            {
                'can_view_users': is_admin,
                'can_edit_user_lab': is_admin,
                'can_edit_lab_cert': is_admin,
                'user_id': request.user.id,
            }
    )

@login_required
@require_http_methods(['GET'])
def user_labs(request, user_id):
    request_user_id = request.user.id
    user_lab_list = api.get_user_labs(request_user_id)
    pi_user_lab_list = api.get_user_labs(request_user_id, is_principal_investigator=True)
    return render(request,
            'lfs_lab_cert_tracker/user_labs.html',
            {
                'user_id': request_user_id,
                'user_lab_list': user_lab_list,
                'pi_user_lab_list': pi_user_lab_list,
            }
    )

@login_required
@require_http_methods(['GET'])
def user_certificates(request, user_id):
    request_user_id = request.user.id
    user_cert_list = api.get_user_certs(request_user_id)
    missing_cert_list = api.get_missing_certs(request_user_id)
    redirect_url = '/users/%d/certificates/' % request_user_id
    user_cert_form = UserCertForm(initial={'user': request_user_id, 'redirect_url': redirect_url})
    return render(request,
            'lfs_lab_cert_tracker/user_certificates.html',
            {
                'user_id': request.user.id,
                'user_cert_list': user_cert_list,
                'missing_cert_list': missing_cert_list,
                'user_cert_form': user_cert_form,
            }
    )

@login_required
@require_http_methods(['GET'])
def labs(request):
    labs = api.get_labs()
    is_admin = auth_utils.is_admin(request.user)
    redirect_url = '/labs/'
    return render(request,
        'lfs_lab_cert_tracker/labs.html',
        {
            'lab_list': labs,
            'can_create_lab': is_admin,
            'lab_form': LabForm(initial={'redirect_url': redirect_url}),
        }
    )

@login_required
@require_http_methods(['GET'])
def certificates(request):
    certs = api.get_certs()
    can_create_cert = auth_utils.is_admin(request.user)
    redirect_url = '/certificates/'
    return render(request,
        'lfs_lab_cert_tracker/certs.html',
        {
            'cert_list': certs,
            'can_create_cert': can_create_cert,
            'cert_form': CertForm(initial={'redirect_url': redirect_url}),
        }
    )

@login_required
@require_http_methods(['GET'])
def users(request):
    is_admin = auth_utils.is_admin(request.user)
    if not is_admin:
        # TODO: Add forbidden page
        return HttpResponseForbidden()
    users = api.get_users()
    can_create_user = request.user.groups.filter(name='admin').exists()
    redirect_url = '/users/'
    return render(request,
        'lfs_lab_cert_tracker/users.html',
        {
            'user_list': users,
            'can_create_user': can_create_user,
            'user_form': UserForm(initial={'redirect_url': redirect_url}),
        }
    )

@login_required
@require_http_methods(['GET'])
def edit_user_labs(request):
    is_admin = auth_utils.is_admin(request.user)
    if not is_admin:
        # TODO: Add forbidden page
        return HttpResponseForbidden()
    users = api.get_users()
    labs = api.get_labs()
    redirect_url = '/users/edit_labs/'
    return render(request,
        'lfs_lab_cert_tracker/edit_user_labs.html',
        {
            'lab_list': labs,
            'user_list': users,
            'user_lab_form': UserLabForm(initial={'redirect_url': redirect_url}),
        }
    )

@login_required
@require_http_methods(['GET'])
def edit_lab_certs(request):
    is_admin = auth_utils.is_admin(request.user)
    if not is_admin:
        # TODO: Add forbidden page
        return HttpResponseForbidden()
    labs = api.get_labs()
    certs = api.get_certs()
    redirect_url = '/labs/edit_certs/'
    return render(request,
            'lfs_lab_cert_tracker/edit_lab_certs.html',
            {
                'lab_list': labs,
                'cert_list': certs,
                'cert_lab_form': LabCertForm(initial={'redirect_url': redirect_url}),
            }
    )

@login_required
@require_http_methods(['GET'])
def lab_details(request, lab_id):
    request_user_id = request.user.id
    is_admin = auth_utils.is_admin(request.user)
    is_pi = auth_utils.is_principal_investigator(request_user_id, lab_id)
    if not is_admin and not is_pi:
        # TODO: Add forbidden page
        return HttpResponseForbidden()

    lab = api.get_lab(lab_id)
    users_in_lab = api.get_users_in_lab(lab_id)
    users_missing_certs = api.get_users_missing_certs(lab_id)
    return render(request,
            'lfs_lab_cert_tracker/lab_details.html',
            {
                'lab': lab,
                'users_in_lab': users_in_lab,
                'users_missing_certs': users_missing_certs,
            }
    )

@login_required
@require_http_methods(['GET'])
def user_cert_details(request, user_id, cert_id):
    request_user_id = request.user.id
    is_admin = auth_utils.is_admin(request.user)
    if request_user_id != user_id and not is_admin:
        # TODO: Add forbidden page
        return HttpResponseForbidden()

    # Retrieve information about the user cert
    user_cert = api.get_user_cert(user_id, cert_id)
    return render(request,
            'lfs_lab_cert_tracker/user_cert_details.html',
            {
                'user_cert': user_cert,
                'user_id': user_id,
            }
    )

@login_required
@require_http_methods(['GET'])
def user_details(request, user_id):
    request_user_id = request.user.id
    is_admin = auth_utils.is_admin(request.user)
    if request_user_id != user_id and not is_admin:
        # TODO: Add forbidden page
        return HttpResponseForbidden()

    user_lab_list = api.get_user_labs(user_id)
    user_cert_list = api.get_user_certs(user_id)
    missing_cert_list = api.get_missing_certs(user_id)
    return render(request,
            'lfs_lab_cert_tracker/user_details.html',
            {
                'user_lab_list': user_lab_list,
                'user_cert_list': user_cert_list,
                'missing_cert_list': missing_cert_list,
                'user_id': request.user.id,
            }
    )
