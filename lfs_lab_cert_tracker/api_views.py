import datetime
import logging
import json
from http import HTTPStatus

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.forms.models import model_to_dict
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from lfs_lab_cert_tracker.forms import UserForm, UserCertForm, CertForm, LabForm, UserLabForm, LabCertForm
from lfs_lab_cert_tracker import api
from lfs_lab_cert_tracker.auth_utils import user_or_admin, admin_only, admin_or_pi_only
from lfs_lab_cert_tracker.redirect_utils import handle_redirect


"""
Provides HTTP endpoints to access the api
"""

logger = logging.getLogger(__name__)

# Users

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def users(request):
    """ Create a new user """

    form = UserForm(request.POST)
    if form.is_valid():
        user = form.save()
        if user:
            messages.success(request, 'Success! Created {0} successfully.'.format(user.username))
            logger.info("%s: Created user %s" % (request.user, user.username))
            return JsonResponse( model_to_dict(user) )
        else:
            messages.error(request, 'Error! Failed to create {0}. Please check your CWL.'.format(user.username))
    else:
        errors = form.errors.get_json_data()
        messages.error(request, 'Error! Form is invalid. {0}'.format( get_error_messages(errors) ) )

    return None

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def delete_user(request, user_id):
    """ Delete a user """

    user = api.get_user(user_id)
    res = api.delete_user(user_id)
    if res:
        messages.success(request, 'Success! Deleted {0} successfully.'.format(user.username))
        logger.info("%s: Deleted user %s" % (request.user, res))
        return JsonResponse(res)
    else:
        messages.error(request, 'Error! Failed to delete {0}.'.format(user.username))

    return None


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def switch_admin(request, user_id):
    """ Switch a user to Admin or not Admin """

    res = api.switch_admin(user_id)
    if res:
        if res['is_superuser']:
            messages.success(request, 'Success! Granted administrator privileges to {0} successfully.'.format(res['username']))
            logger.info("%s: Granted administrator privileges for %s" % (request.user, res['id']))
        else:
            messages.success(request, 'Success! Revoked administrator privileges of {0} successfully.'.format(res['username']))
            logger.info("%s: Revoked administrator privileges %s" % (request.user, res['id']))
        return JsonResponse({'user_id': res['id']})

    else:
        messages.error(request, 'Error! Failed to switch an admin role for {0}.'.format(res['username']))
    return None



@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def switch_inactive(request, user_id=None):
    """ Switch a user to Active or Inactive """

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

# Users and Labs

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@admin_or_pi_only
@handle_redirect
@require_http_methods(['POST'])
def user_labs(request, lab_id=None):
    """ Add a user to a lab """

    data = request.POST
    user = api.get_user_by_username(data['user'].strip())

    # Check whether a user exists or not
    if user:
        res = api.create_user_lab(user.id, lab_id, data['role'])
        if res:
            valid_email = False
            valid_email_errors = []
            try:
                validate_email(user.email)
                valid_email = True
            except ValidationError as e:
                 valid_email_errors = e

            if valid_email:
                messages.success(request, 'Success! Added {0} successfully.'.format(data['user']))
            else:
                messages.warning(request, 'Warning! Added {0} successfully, but failed to send an email. ({1} is invalid)'.format(data['user'], user.email))

            logger.info("%s: Created user lab %s" % (request.user, res))
            return JsonResponse(res)
        else:
            messages.error(request, 'Error! Failed to add {0}. CWL has already existed in this lab.'.format(data['user']))
    else:
        messages.error(request, 'Error! Failed to add {0}. CWL does not exist.'.format(data['user']))

    return None


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
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


# Users and Certificates

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
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
        messages.error(request, "Error! Failed to add a certificate. If you try to update a new certificate, please delete your old certificate first.")


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_or_admin
@handle_redirect
@require_http_methods(['POST'])
def delete_user_certs(request, user_id=None, cert_id=None):
    res = api.delete_user_cert(user_id, cert_id)
    if res:
        cert = api.get_cert(cert_id)
        messages.success(request, 'Success! Deleted {0} successfully.'.format(cert['name']))
        return JsonResponse(res)
    return None


# Labs

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def labs(request, lab_id=None):
    """ Create a new lab """

    form = LabForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data
        lab = form.save()
        if lab:
            messages.success(request, 'Success! Created {0} successfully.'.format(lab.name))
            logger.info("%s: Created lab %s" % (request.user, lab.name))
            return JsonResponse( model_to_dict(lab) )
        else:
            messages.error(request, 'Error! Failed to create {0}.'.format(lab.name))
    else:
        errors = form.errors.get_json_data()
        messages.error(request, 'Error! Form is invalid. {0}.'.format(get_error_messages(errors)))
    return None


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def delete_labs(request, lab_id=None):
    """ Delete a lab """

    lab = api.get_lab(lab_id)
    res = api.delete_lab(lab_id)
    if res:
        messages.success(request, 'Success! Deleted {0} successfully.'.format(lab.name))
        logger.info("%s: Deleted lab %s" % (request.user, res))
        return JsonResponse(res)
    else:
        messages.error(request, 'Error! Failed to delete {0}.'.format(lab.name))
    return None



@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def update_labs(request, lab_id):
    """ Update a lab's name """

    form = LabForm(request.POST, instance=api.get_lab(lab_id))
    if form.is_valid():
        lab = form.save()
        if lab:
            messages.success(request, 'Success! Updated {0} successfully.'.format(lab.name))
            logger.info("%s: Updated lab %s" % (request.user, lab.name))
            return JsonResponse( model_to_dict(lab) )
        else:
            messages.error(request, 'Error! Failed to update {0}.'.format(lab.name))
    else:
        errors = form.errors.get_json_data()
        messages.error(request, 'Error! Form is invalid. {0}.'.format(get_error_messages(errors)))

    return None

# Certificates

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def certs(request):
    """ Create a new certificate """

    form = CertForm(request.POST)
    if form.is_valid():
        cert = form.save()
        if cert:
            messages.success(request, 'Success! Created {0} successfully.'.format(cert.name))
            logger.info("%s: Created cert %s" % (request.user, cert.name))
            return JsonResponse( model_to_dict(cert) )
        else:
            messages.error(request, 'Error! Failed to create {0}. This cert has already existed.'.format(cert.name))
    else:
        errors = form.errors.get_json_data()
        messages.error(request, 'Error! Form is invalid. {0}'.format(get_error_messages(errors)))

    return None


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@admin_only
@handle_redirect
@require_http_methods(['POST'])
def delete_certs(request, cert_id):
    """ Delete a certificate """

    cert = api.get_cert(cert_id)
    res = api.delete_cert(cert_id)
    if res:
        messages.success(request, 'Success! Deleted {0} successfully.'.format(cert['name']))
        logger.info("%s: Deleted cert %s" % (request.user, res))
        return JsonResponse(res)
    else:
        messages.error(request, 'Error! Failed to delete {0}.'.format(cert['name']))
    return None





# Labs and Certificates

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@admin_or_pi_only
@handle_redirect
@require_http_methods(['POST'])
def lab_certs(request, lab_id):
    """ Add a certificate to a lab """

    data = request.POST
    res = api.create_lab_cert(lab_id, data['cert'])
    cert = api.get_cert(data['cert'])
    if res:
        messages.success(request, 'Success! Added {0} successfully.'.format(cert['name']))
        logger.info("%s: Created lab cert %s" % (request.user, res))
        return JsonResponse(res)
    else:
        messages.error(request, 'Error! Failed to add {0}. This cert has already existed.'.format(cert['name']))

    return None


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@admin_or_pi_only
@handle_redirect
@require_http_methods(['POST'])
def delete_lab_certs(request, lab_id, cert_id):
    """ Delete a certificate in a lab """

    cert = api.get_cert(cert_id)
    res = api.delete_lab_cert(lab_id, cert_id)
    if res:
        messages.success(request, 'Success! Delete {0} successfully.'.format(cert['name']))
        logger.info("%s: Deleted lab cert %s" % (request.user, res))
        return JsonResponse(res)
    else:
        messages.error(request, 'Error! Failed to delete {0}.'.format(cert['name']))
    return None


# Helper methods

def get_error_messages(errors):
    messages = ''
    for key in errors.keys():
        value = errors[key]
        messages += value[0]['message'] + ' '
    return messages.strip()
