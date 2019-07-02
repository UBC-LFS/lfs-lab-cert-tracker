import datetime

import logging

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods

from lfs_lab_cert_tracker.forms import UserForm, UserCertForm, CertForm, LabForm, UserLabForm
from lfs_lab_cert_tracker import api
from lfs_lab_cert_tracker.auth_utils import user_or_admin, admin_only, admin_or_pi_only
from lfs_lab_cert_tracker.redirect_utils import handle_redirect

from http import HTTPStatus
import json
from django.contrib import messages
from django.forms.models import model_to_dict

"""
Provides HTTP endpoints to access the api
"""

logger = logging.getLogger(__name__)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def certs(request):
    form = CertForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data
        res = api.create_cert(data['name'], data['expiry_in_years'])
        if res:
            messages.success(request, 'Success! Created {0} successfully.'.format(data['name']))
            logger.info("%s: Created cert %s" % (request.user, res))
            return JsonResponse(res)
        else:
            messages.error(request, 'Error! Failed to create {0}. This cert has already existed.'.format(data['name']))
    else:
        errors = form.errors.get_json_data()
        messages.error(request, 'Error! Form is invalid. {0}'.format(get_error_messages(errors)))
    return None


@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def delete_certs(request, cert_id=None):
    cert = api.get_cert(cert_id)
    res = api.delete_cert(cert_id)
    if res:
        messages.success(request, 'Success! Deleted {0} successfully.'.format(cert['name']))
        logger.info("%s: Deleted cert %s" % (request.user, res))
    else:
        messages.error(request, 'Error! Failed to delete {0}.'.format(cert['name']))

    return JsonResponse(res)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def delete_user(request, user_id=None):
    user = model_to_dict( api.get_user(user_id) )
    res = api.delete_user(user_id)
    if res:
        messages.success(request, 'Success! Deleted {0} successfully.'.format(user['username']))
        logger.info("%s: Deleted user %s" % (request.user, res))
    else:
        messages.error(request, 'Error! Failed to delete {0}.'.format(user['username']))

    return JsonResponse(res)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def switch_admin(request, user_id=None):
    res = api.switch_admin(user_id)
    if res:
        if res['is_superuser']:
            messages.success(request, 'Success! Switched to Admin for {0} successfully.'.format(res['username']))
            logger.info("%s: Switched to Admin for %s" % (request.user, res['id']))
        else:
            messages.success(request, 'Success! Admin is canceled for {0} successfully.'.format(res['username']))
            logger.info("%s: Admin is canceled %s" % (request.user, res['id']))
    else:
        messages.error(request, 'Error! Failed to switch {0}.'.format(res['username']))

    return JsonResponse({'user_id': res['id']})

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def switch_inactive(request, user_id=None):
    res = api.switch_inactive(user_id)
    if res:
        if res['is_active']:
            messages.success(request, 'Success! {0} became ACTIVE successfully.'.format(res['username']))
            logger.info("%s: Became active %s" % (request.user, res['id']))
        else:
            messages.success(request, 'Success! {0} became INACTIVE successfully.'.format(res['username']))
            logger.info("%s: Became inactive  %s" % (request.user, res['id']))
        return JsonResponse({'user_id': res['id']})
    else:
        messages.error(request, 'Error! Failed to switch {0}.'.format(res['username']))

    return None


@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def labs(request, lab_id=None):
    print(request.POST)
    form = LabForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data
        res = api.create_lab(data['name'])
        if res:
            messages.success(request, 'Success! Created {0} successfully.'.format(data['name']))
            logger.info("%s: Created lab %s" % (request.user, res))
            return JsonResponse(res)
        else:
            messages.error(request, 'Error! Failed to create {0}.'.format(data['name']))
    else:
        errors = form.errors.get_json_data()
        messages.error(request, 'Error! Form is invalid. {0}.'.format(get_error_messages(errors)))
    return None


@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def delete_labs(request, lab_id=None):
    lab = api.get_lab(lab_id)
    res = api.delete_lab(lab_id)
    if res:
        messages.success(request, 'Success! Deleted {0} successfully.'.format(lab['name']))
        logger.info("%s: Deleted lab %s" % (request.user, res))
    else:
        messages.error(request, 'Error! Failed to delete {0}.'.format(lab['name']))

    return JsonResponse(res)

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def update_labs(request, lab_id=None):
    form = LabForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data
        res = api.update_lab(lab_id, data['name'])
        if res:
            messages.success(request, 'Success! Updated {0} successfully.'.format(data['name']))
            logger.info("%s: Updated lab %s" % (request.user, res))
            return JsonResponse(res)
        else:
            messages.error(request, 'Error! Failed to update {0}.'.format(data['name']))
    else:
        errors = form.errors.get_json_data()
        messages.error(request, 'Error! Form is invalid. {0}.'.format(get_error_messages(errors)))

    return None




@login_required
@admin_or_pi_only
@handle_redirect
@require_http_methods(['POST'])
def lab_certs(request, lab_id=None):
    data = request.POST
    res = api.create_lab_cert(lab_id, data['cert'])
    cert = api.get_cert(data['cert'])
    if res:
        messages.success(request, 'Success! Added {0} successfully.'.format(cert['name']))
        logger.info("%s: Created lab cert %s" % (request.user, res))
        return JsonResponse(res)
    else:
        messages.error(request, 'Error! Failed to add {0}. This cert has already existed.'.format(cert['name']))


@login_required
@admin_or_pi_only
@handle_redirect
@require_http_methods(['POST'])
def delete_lab_certs(request, lab_id=None, cert_id=None):
    cert = api.get_cert(cert_id)
    res = api.delete_lab_cert(lab_id, cert_id)
    if res:
        messages.success(request, 'Success! Delete {0} successfully.'.format(cert['name']))
        logger.info("%s: Deleted lab cert %s" % (request.user, res))
        return JsonResponse(res)
    else:
        messages.error(request, 'Error! Failed to delete {0}.'.format(cert['name']))



@login_required
@user_or_admin
@handle_redirect
@require_http_methods(['POST'])
def user_certs(request, user_id=None):
    form = UserCertForm(request.POST, request.FILES)

    # Whether form is valid or not
    if form.is_valid():
        data = request.POST
        files = request.FILES
        cert = api.get_cert(data['cert'])

        year = int(data['completion_date_year'])
        month = int(data['completion_date_month'])
        day = int(data['completion_date_day'])

        completion_date = datetime.datetime(year=year, month=month, day=day)

        # Calculate a expiry year
        expiry_year = year + int(cert['expiry_in_years'])
        expiry_date = datetime.datetime(year=expiry_year, month=month, day=day)

        result = api.update_or_create_user_cert(data['user'], data['cert'], files['cert_file'], completion_date, expiry_date)

        # Whether user's certficiate is created successfully or not
        if result:
            messages.success(request, 'Success! Added {0} successfully.'.format(cert['name']))
            res = { 'user_id': user_id, 'cert_id': result['cert'] }
            logger.info("%s: Created user cert %s" % (request.user, res))
            return JsonResponse(res)
        else:
            messages.error(request, "Error! Failed to add a certificate.")
    else:
        messages.error(request, "Error! Failed to add a certificate. Please check error messages below.")


@login_required
@user_or_admin
@handle_redirect
@require_http_methods(['POST'])
def delete_user_certs(request, user_id=None, cert_id=None):
    res = api.delete_user_cert(user_id, cert_id)
    if res['result']:
        cert = api.get_cert(cert_id)
        messages.success(request, 'Success! Deleted {0} successfully.'.format(cert['name']))

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
def user_labs(request, lab_id=None):
    data = request.POST
    user = api.get_user_by_username(data['user'].strip())

    form = UserLabForm(data)
    print("is valid()", form.is_valid())
    print("errors ", form.errors.get_json_data())

    # Check whether a user exists or not
    if user:
        print("user ", user)
        res = api.create_user_lab(user.id, lab_id, data['role'])
        if res:
            messages.success(request, 'Success! Added {0} successfully.'.format(data['user']))
            logger.info("%s: Created user lab %s" % (request.user, res))
            return JsonResponse(res)
        else:
            messages.error(request, 'Error! Failed to add {0}. CWL has already existed in this lab.'.format(data['user']))
    else:
        messages.error(request, 'Error! Failed to add {0}. CWL does not exist.'.format(data['user']))

    return None


@login_required
@admin_or_pi_only
@handle_redirect
@require_http_methods(['POST'])
def delete_user_lab(request, user_id=None, lab_id=None):
    user = model_to_dict( api.get_user(user_id) )
    res = api.delete_user_lab(user_id, lab_id)
    if res:
        messages.success(request, 'Success! Delete {0} successfully.'.format(user['username']))
        logger.info("%s: Deleted user lab %s" % (request.user, res))
        return JsonResponse(res)
    else:
        messages.error(request, 'Error! Failed to delete {0}.'.format(user['username']))

@login_required
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def users(request):
    form = UserForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data
        res = api.create_user(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            username=data['username']
        )
        if res:
            messages.success(request, 'Success! Created {0} successfully.'.format(data['username']))
            logger.info("%s: Created user %s" % (request.user, res))
            return JsonResponse(res)
        else:
            messages.error(request, 'Error! Failed to create {0}. Please check your CWL.'.format(data['username']))
    else:
        errors = form.errors.get_json_data()
        messages.error(request, 'Error! Form is invalid. {0}'.format( get_error_messages(errors) ) )

    return None


def get_error_messages(errors):
    messages = ''
    for key in errors.keys():
        value = errors[key]
        messages += value[0]['message'] + ' '
    return messages.strip()
