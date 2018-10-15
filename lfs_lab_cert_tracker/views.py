from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render

from lfs_lab_cert_tracker import api
from lfs_lab_cert_tracker.forms import (LabForm, CertForm, UserForm,
        UserLabForm, LabCertForm, UserCertForm)

@login_required
@require_http_methods(['GET'])
def index(request):
    can_view_users = request.user.groups.filter(name='admin').exists()
    can_edit_user_lab = request.user.groups.filter(name='admin').exists()
    can_edit_lab_cert = request.user.groups.filter(name='admin').exists()
    return render(request,
            'lfs_lab_cert_tracker/index.html',
            {
                'user_id': request.user.id,
                'can_view_users': can_view_users,
                'can_edit_user_lab': can_edit_user_lab,
                'can_edit_lab_cert': can_edit_lab_cert,
            }
    )

@login_required
@require_http_methods(['GET'])
def user_labs(request, user_id):
    request_user_id = request.user.id
    user_lab_list = api.get_user_labs(request_user_id)
    return render(request,
            'lfs_lab_cert_tracker/user_labs.html',
            {
                'user_id': request_user_id,
                'user_lab_list': user_lab_list,
            }
    )

@login_required
@require_http_methods(['GET'])
def user_certificates(request, user_id):
    request_user_id = request.user.id
    user_cert_list = api.get_user_certs(request_user_id)
    missing_cert_list = api.get_missing_certs(request_user_id)
    post_redirect_url = '/users/%d/certificates/' % request_user_id
    user_cert_form = UserCertForm(initial={'user': request_user_id, 'redirect_url': post_redirect_url})
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
    can_create_lab = request.user.groups.filter(name='admin').exists()
    return render(request,
        'lfs_lab_cert_tracker/labs.html',
        {
            'lab_list': labs,
            'can_create_lab': can_create_lab,
            'lab_form': LabForm(),
        }
    )

@login_required
@require_http_methods(['GET'])
def certificates(request):
    certs = api.get_certs()
    can_create_cert = request.user.groups.filter(name='admin').exists()
    return render(request,
        'lfs_lab_cert_tracker/certs.html',
        {
            'cert_list': certs,
            'can_create_cert': can_create_cert,
            'cert_form': CertForm(),
        }
    )

@login_required
@permission_required('lfs_lab_cert_tracker.view_user')
@require_http_methods(['GET'])
def users(request):
    users = api.get_users()
    can_create_user = request.user.groups.filter(name='admin').exists()
    return render(request,
        'lfs_lab_cert_tracker/users.html',
        {
            'user_list': users,
            'can_create_user': can_create_user,
            'user_form': UserForm(),
        }
    )

@login_required
@permission_required('lfs_lab_cert_tracker.add_userlab')
@require_http_methods(['GET'])
def edit_user_labs(request):
    users = api.get_users()
    labs = api.get_labs()
    return render(request,
        'lfs_lab_cert_tracker/edit_user_labs.html',
        {
            'lab_list': labs,
            'user_list': users,
            'user_lab_form': UserLabForm(),
        }
    )

@login_required
@permission_required('lfs_lab_cert_tracker.add_labcert')
@require_http_methods(['GET'])
def edit_lab_certs(request):
    labs = api.get_labs()
    certs = api.get_certs()
    return render(request,
            'lfs_lab_cert_tracker/edit_lab_certs.html',
            {
                'lab_list': labs,
                'cert_list': certs,
                'cert_lab_form': LabCertForm(),
            }
    )

