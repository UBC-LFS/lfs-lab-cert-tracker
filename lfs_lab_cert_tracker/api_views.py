import datetime
import json
from io import StringIO
import tempfile

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from lfs_lab_cert_tracker import api
from lfs_lab_cert_tracker.auth_utils import user_or_admin, admin_only
from lfs_lab_cert_tracker.redirect_utils import handle_redirect

"""
Provides HTTP endpoints to access the api
"""

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def certs(request, cert_id=None):
    data = request.POST
    res = api.create_cert(data['name'])
    return JsonResponse(res)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def delete_certs(request, cert_id=None):
    data = request.POST
    res = api.delete_cert(cert_id)
    return JsonResponse(res)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def labs(request, lab_id=None):
    data = request.POST
    res = api.create_lab(data['name'])
    return JsonResponse(res)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def delete_labs(request, lab_id=None):
    data = request.POST
    res = api.delete_lab(lab_id)
    return JsonResponse(res)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def lab_certs(request, lab_id=None, cert_id=None):
    data = request.POST
    res = api.create_lab_cert(lab_id, data['cert'])
    return JsonResponse(res)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def delete_lab_certs(request, lab_id=None, cert_id=None):
    data = request.POST
    res = api.delete_lab_cert(lab_id, cert_id)
    return JsonResponse(res)

@login_required
@user_or_admin
@handle_redirect
@require_http_methods(['POST'])
def user_certs(request, user_id=None, cert_id=None):
    data = request.POST
    files = request.FILES
    expiry_date = None
    if all([data['expiry_date_year'], data['expiry_date_month'], data['expiry_date_day']]):
        expiry_date = datetime.datetime(year=int(data['expiry_date_year']), month=int(data['expiry_date_month']), day=int(data['expiry_date_day']))
    res = api.update_or_create_user_cert(data['user'], data['cert'], files['cert_file'], expiry_date)
    # Added since uploading files with ajax is a pain
    # So in this case just redirect to the client specified url
    response = {
        'user_id': user_id,
        'cert_id': cert_id,
    }
    return JsonResponse(response)

@login_required
@user_or_admin
@handle_redirect
@require_http_methods(['POST'])
def delete_user_certs(request, user_id=None, cert_id=None):
    data = request.POST
    res = api.delete_user_cert(user_id, cert_id)

    return JsonResponse(res)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def user_labs(request, user_id=None, lab_id=None):
    data = request.POST
    res = api.create_user_lab(data['user'], lab_id, data['role'])
    return JsonResponse(res)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def delete_user_lab(request, user_id=None, lab_id=None):
    data = request.POST
    res = api.delete_user_lab(user_id, lab_id)
    return JsonResponse(res)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def users(request):
    data = request.POST
    res = api.create_user(
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email'],
        cwl=data['cwl'],
    )
    return JsonResponse(res)
