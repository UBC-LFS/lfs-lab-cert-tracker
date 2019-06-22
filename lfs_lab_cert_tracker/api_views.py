import datetime

import logging

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods

from lfs_lab_cert_tracker.forms import UserForm, UserCertForm
from lfs_lab_cert_tracker import api
from lfs_lab_cert_tracker.auth_utils import user_or_admin, admin_only, admin_or_pi_only
from lfs_lab_cert_tracker.redirect_utils import handle_redirect

from http import HTTPStatus
import json

"""
Provides HTTP endpoints to access the api
"""

logger = logging.getLogger(__name__)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def certs(request, cert_id=None):
    data = request.POST
    res = api.create_cert(data['name'])
    logger.info("%s: Created cert %s" % (request.user, res))
    #print("certs: ", res)
    return JsonResponse(res)
    #return HttpResponse( json.dumps(res), content_type="application/json" )

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def delete_certs(request, cert_id=None):
    data = request.POST
    res = api.delete_cert(cert_id)
    logger.info("%s: Deleted cert %s" % (request.user, res))
    return JsonResponse(res)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def delete_user(request, user_id=None):
    data = request.POST
    res = api.delete_user(user_id)
    logger.info("%s: Deleted user %s" % (request.user, res))
    return JsonResponse(res)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def switch_admin(request, user_id=None):
     data = request.POST
     res = api.switch_admin(user_id)
     return JsonResponse(res)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def switch_inactive(request, user_id=None):
    data = request.POST
    res = api.switch_inactive(user_id)
    return JsonResponse(res)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def labs(request, lab_id=None):
    data = request.POST
    res = api.create_lab(data['name'])
    logger.info("%s: Created lab %s" % (request.user, res))
    return JsonResponse(res)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def delete_labs(request, lab_id=None):
    data = request.POST
    res = api.delete_lab(lab_id)
    logger.info("%s: Deleted lab %s" % (request.user, res))
    return JsonResponse(res)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def update_labs(request, lab_id=None):
    data = request.POST
    res = api.update_lab(lab_id, data['name'])
    logger.info("%s: Updated lab %s" % (request.user, res))
    return JsonResponse(res)

@login_required
@admin_or_pi_only
@handle_redirect
@require_http_methods(['POST'])
def lab_certs(request, lab_id=None, cert_id=None):
    data = request.POST
    res = api.create_lab_cert(lab_id, data['cert'])
    logger.info("%s: Created lab cert %s" % (request.user, res))
    return JsonResponse(res)

@login_required
@admin_or_pi_only
@handle_redirect
@require_http_methods(['POST'])
def delete_lab_certs(request, lab_id=None, cert_id=None):
    data = request.POST
    res = api.delete_lab_cert(lab_id, cert_id)
    logger.info("%s: Deleted lab cert %s" % (request.user, res))
    return JsonResponse(res)


"""
@login_required
@user_or_admin
@handle_redirect
@require_http_methods(['POST'])
def user_certs(request, user_id=None, cert_id=None):
    data = request.POST
    files = request.FILES
    completion_date = None
    expiry_date = None
    cert = api.get_cert(data['cert'])

    if all([data['completion_date_year'], data['completion_date_month'], data['completion_date_day']]):
        completion_date = datetime.datetime(year=int(data['completion_date_year']), month=int(data['completion_date_month']), day=int(data['completion_date_day']))
        year = int(data['completion_date_year']) + int(cert['expiry_in_years'])
        expiry_date = datetime.datetime(year=year, month=int(data['completion_date_month']), day=int(data['completion_date_day']))

    #print(data['user'], data['cert'], files['cert_file'], completion_date, expiry_date)
    res = api.update_or_create_user_cert(data['user'], data['cert'], files['cert_file'], completion_date, expiry_date)
    res = { 'user_id': user_id, 'cert_id': cert_id }
    logger.info("%s: Created user cert %s" % (request.user, res))
    return JsonResponse(res)
"""


@login_required
@user_or_admin
@handle_redirect
@require_http_methods(['POST'])
def delete_user_certs(request, user_id=None, cert_id=None):
    data = request.POST
    res = api.delete_user_cert(user_id, cert_id)
    logger.info("%s: Deleted user cert %s" % (request.user, res))
    return JsonResponse(res)

@login_required
@user_or_admin
@handle_redirect
@require_http_methods(['POST'])
def update_user_certs(request, user_id=None, cert_id=None):
    data = request.POST
    #print(data, user_id, cert_id)
    #res = api.delete_user_cert(user_id, cert_id)
    #logger.info("%s: Deleted user cert %s" % (request.user, res))
    return JsonResponse(res)

@login_required
@admin_or_pi_only
@handle_redirect
@require_http_methods(['POST'])
def user_labs(request, user_id=None, lab_id=None):
    data = request.POST
    user = api.get_user_by_cwl(data['user'])
    res = api.create_user_lab(user.id, lab_id, data['role'])
    logger.info("%s: Created user lab %s" % (request.user, res))
    return JsonResponse(res)

@login_required
@admin_or_pi_only
@handle_redirect
@require_http_methods(['POST'])
def delete_user_lab(request, user_id=None, lab_id=None):
    data = request.POST
    res = api.delete_user_lab(user_id, lab_id)
    logger.info("%s: Deleted user lab %s" % (request.user, res))
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
        username=data['username'],
    )
    logger.info("%s: Created user %s" % (request.user, res))
    return JsonResponse(res)
