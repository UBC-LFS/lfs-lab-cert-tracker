from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render

from lfs_lab_cert_tracker import api
from lfs_lab_cert_tracker.forms import LabForm, CertForm

@login_required
@require_http_methods(['GET'])
def index(request):
    return render(request,
            'lfs_lab_cert_tracker/index.html',
            {
                'user_id': request.user.id,
            }
    )

@login_required
@require_http_methods(['GET'])
def user_labs(request, user_id):
    request_user_id = request.user.id
    return render(request,
            'lfs_lab_cert_tracker/user_labs.html',
            {
                'user_id': request_user_id,
                'user_lab_list': api.get_user_labs(request_user_id),
            }
    )

@login_required
@require_http_methods(['GET'])
def user_certificates(request, user_id):
    request_user_id = request.user.id
    return render(request,
            'lfs_lab_cert_tracker/user_certificates.html',
            {
                'user_id': request.user.id,
                'user_cert_list': api.get_user_certs(request_user_id),
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
