from io import BytesIO
from cgi import escape
from xhtml2pdf import pisa

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.shortcuts import render, redirect
from django.views.static import serve
from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.db.models import Q
from django.contrib.auth import authenticate, login as DjangoLogin
from django.contrib.auth.models import User as AuthUser
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.urls import reverse
from django.core.validators import validate_email

from lfs_lab_cert_tracker import api
from lfs_lab_cert_tracker import auth_utils
from lfs_lab_cert_tracker.forms import *

from lfs_lab_cert_tracker.models import Lab, Cert, UserCert

"""
HTTP endpoints, responsible for the frontend
"""

def login(request):
    return render(request, 'lfs_lab_cert_tracker/login.html')

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@require_http_methods(['GET'])
def index(request):
    return redirect('/users/%d' % (request.user.id))

# Users
@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@auth_utils.admin_only
@require_http_methods(['GET', 'POST'])
def users(request):
    """ Display all users """

    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save()
            if user:
                messages.success(request, 'Success! {0} created.'.format(user.username))
                #return HttpResponseRedirect( reverse('users') + '?t=all' )
                return HttpResponseRedirect(request.get_full_path())
            else:
                messages.error(request, 'Error! Failed to create {0}. Please check your CWL.'.format(user.username))
        else:
            errors = form.errors.get_json_data()
            messages.error(request, 'Error! Form is invalid. {0}'.format( api.get_error_messages(errors) ) )

        return HttpResponseRedirect(request.get_full_path())

    else:
        current_tab = request.GET.get('t')
        api.can_req_parameters_access(request, ['t'])

        user_list = AuthUser.objects.all().order_by('last_name', 'first_name')

        # Find users who have missing certs
        users_in_missing_training = []
        if current_tab == 'report':
            for user in api.add_missing_certs(user_list):
                if user.missing_certs != None:
                    users_in_missing_training.append(user)

            user_list = users_in_missing_training.copy()

        # Pagination enables
        query = request.GET.get('q')
        if query:
            user_list = AuthUser.objects.filter(
                Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
            ).order_by('id').distinct()

        page = request.GET.get('page', 1)
        paginator = Paginator(user_list, 50) # Set 50 users in a page

        try:
            users = paginator.page(page)
        except PageNotAnInteger:
            users = paginator.page(1)
        except EmptyPage:
            users = paginator.page(paginator.num_pages)

        if current_tab == 'all':
            users = api.add_inactive_users(users)
            users = api.add_missing_certs(users)

    return render(request, 'lfs_lab_cert_tracker/users.html', {
        'loggedin_user': request.user,
        'users': users,
        'total_users': len(user_list),
        'users_in_missing_training': users_in_missing_training,
        'user_form': UserForm(),
        'current_tab': current_tab
    })

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@auth_utils.admin_only
@require_http_methods(['POST'])
def edit_user(request):
    ''' Delete a user '''
    if request.method == 'POST':
        user_id = request.POST.get('user')
        user = api.get_user_404(user_id)
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            if form.save():
                messages.success(request, 'Success! {0} updated.'.format(user.get_full_name()))
            else:
                messages.error(request, 'Error! Failed to update {0}.'.format(user.get_full_name()))
        else:
            errors = form.errors.get_json_data()
            messages.error(request, 'Error! Form is invalid. {0}'.format( api.get_error_messages(errors) ))

    return HttpResponseRedirect( request.POST.get('next') )


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@auth_utils.admin_only
@require_http_methods(['POST'])
def delete_user(request):
    ''' Delete a user '''
    if request.method == 'POST':
        user_id = request.POST.get('user')
        user = api.get_user(user_id)
        if api.delete_user(user_id):
            messages.success(request, 'Success! {0} deleted.'.format(user.get_full_name()))
        else:
            messages.error(request, 'Error! Failed to delete {0}.'.format(user.get_full_name()))

    return HttpResponseRedirect( request.POST.get('next') )


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@auth_utils.admin_only
@require_http_methods(['POST'])
def switch_admin(request):
    ''' Switch a user to Admin or not Admin '''
    if request.method == 'POST':
        user_id = request.POST.get('user')
        res = api.switch_admin(user_id)
        if res:
            if res['is_superuser']:
                messages.success(request, 'Success! Granted administrator privileges to {0}.'.format(res['username']))
            else:
                messages.success(request, 'Success! Revoked administrator privileges of {0}.'.format(res['username']))
        else:
            messages.error(request, 'Error! Failed to switch an admin role for {0}.'.format(res['username']))

    return HttpResponseRedirect( request.POST.get('next') )


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@auth_utils.admin_only
@require_http_methods(['POST'])
def switch_inactive(request):
    ''' Switch a user to Active or Inactive '''
    if request.method == 'POST':
        user_id = request.POST.get('user')
        res = api.switch_inactive(user_id)
        if res:
            if res['is_active']:
                messages.success(request, 'Success! {0} is now ACTIVE.'.format(res['username']))
            else:
                messages.success(request, 'Success! {0} is now INACTIVE.'.format(res['username']))
        else:
            messages.error(request, 'Error! Failed to switch {0}.'.format(res['username']))

    return HttpResponseRedirect( request.POST.get('next') )


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
#@auth_utils.user_or_admin
@auth_utils.admin_or_pi_or_user
@require_http_methods(['GET'])
def user_details(request, user_id):
    """ Display user's details """
    app_user = api.get_user(user_id)

    return render(request, 'lfs_lab_cert_tracker/user_details.html', {
        'loggedin_user': request.user,
        'app_user': app_user,
        'user_lab_list': api.get_user_labs(user_id),
        'pi_user_lab_list': api.get_user_labs(user_id, is_principal_investigator=True),
        'user_cert_list': api.get_user_certs(user_id),
        'missing_cert_list': api.get_missing_certs(user_id),
        'expired_cert_list': api.get_expired_certs(user_id)
    })

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@auth_utils.user_or_admin
@require_http_methods(['GET'])
def user_labs(request, user_id):
    """ Display user's labs """
    if api.get_user(user_id) is None: raise Http404

    return render(request, 'lfs_lab_cert_tracker/user_labs.html', {
        'loggedin_user': request.user,
        'user_lab_list': api.get_user_labs(request.user.id),
        'pi_user_lab_list': api.get_user_labs(request.user.id, is_principal_investigator=True)
    })

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@auth_utils.user_or_admin
@require_http_methods(['GET'])
def user_certs(request, user_id):
    """ Display user's certificates """
    if api.get_user(user_id) is None:
        raise Http404

    if request.user.id != user_id:
        if not auth_utils.is_admin(request.user): raise PermissionDenied

    return render(request, 'lfs_lab_cert_tracker/user_certs.html', {
        'loggedin_user': request.user,
        'user_id': user_id,
        'user': api.get_user(user_id),
        'user_cert_list': api.get_user_certs(user_id),
        'missing_cert_list': api.get_missing_certs(user_id),
        'expired_cert_list': api.get_expired_certs(user_id),
        'user_cert_form': UserCertForm(None, initial={
            'user': user_id,
            #'cert': api.get_missing_certs(user_id),
            'redirect_url': '/users/%d/training-record/' % user_id
        })
    })

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
#@auth_utils.user_or_admin
@auth_utils.admin_or_pi_or_user
@require_http_methods(['GET'])
def user_cert_details(request, user_id, cert_id):
    loggedin_user_id = request.user.id
    redirect_url = '/users/%d/training-record/' % loggedin_user_id

    user_cert = api.get_user_cert(user_id, cert_id)
    if not user_cert:
        raise Http404

    return render(request, 'lfs_lab_cert_tracker/user_cert_details.html', {
        'loggedin_user': request.user,
        'app_user': api.get_user(user_id),
        'user_cert': api.get_user_cert(user_id, cert_id),
        'delete_user_cert_form': DeleteUserCertForm(initial={'redirect_url': redirect_url})
    })

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
#@auth_utils.user_or_admin
@auth_utils.admin_or_pi_or_user
@require_http_methods(['GET'])
def user_report(request, user_id=None):
    """ Download user's report as PDF """
    app_user = api.get_user(user_id)
    if app_user is None:
        raise PermissionDenied

    missing_cert_list = api.get_missing_certs(user_id)
    user_cert_list = api.get_user_certs(user_id)
    user_cert_ids = set([uc['id'] for uc in user_cert_list])
    expired_cert_ids = set([ec['id'] for ec in api.get_expired_certs(user_id)])

    user_lab_list = api.get_user_labs(user_id)
    user_labs = []
    for user_lab in user_lab_list:
        lab_certs = api.get_lab_certs(user_lab['id'])
        missing_lab_certs = []
        for lc in lab_certs:
            if lc['id'] not in user_cert_ids or lc['id'] in expired_cert_ids:
                missing_lab_certs.append(lc)
        user_labs.append((user_lab, lab_certs, missing_lab_certs))

    return render_to_pdf('lfs_lab_cert_tracker/user_report.html', {
        'user_cert_list': user_cert_list,
        'app_user': app_user,
        'user_labs': user_labs
    })


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@auth_utils.admin_only
@require_http_methods(['GET'])
def users_in_missing_training_report(request):
    users = AuthUser.objects.all().order_by('last_name', 'first_name')

    # Find users who have missing certs
    users_in_missing_training = []
    for user in api.add_missing_certs(users):
        if user.missing_certs != None:
            users_in_missing_training.append(user)

    return render_to_pdf('lfs_lab_cert_tracker/users_in_missing_training_report.html', {
        'users': users_in_missing_training,
    })

def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    context = Context(context_dict)
    html  = template.render(context_dict)
    response = BytesIO()

    pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), response)
    if not pdf.err:
        return HttpResponse(response.getvalue(), content_type='application/pdf')
    return HttpResponse('Encountered errors <pre>%s</pre>' % escape(html))


# Labs

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@require_http_methods(['GET'])
def labs(request):
    """ Display all labs """

    is_admin = auth_utils.is_admin(request.user)
    redirect_url = '/all-areas/'

    lab_list = api.get_labs()

    # Pagination enables
    query = request.GET.get('q')
    if query:
        lab_list = Lab.objects.filter( Q(name__icontains=query) ).distinct()

    page = request.GET.get('page', 1)
    paginator = Paginator(lab_list, 50) # Set 50 labs in a page
    try:
        labs = paginator.page(page)
    except PageNotAnInteger:
        labs = paginator.page(1)
    except EmptyPage:
        labs = paginator.page(paginator.num_pages)

    return render(request, 'lfs_lab_cert_tracker/labs.html', {
        'loggedin_user': request.user,
        'labs': labs,
        'total_labs': len(lab_list),
        'can_create_lab': is_admin,
        'lab_form': LabForm(initial={'redirect_url': redirect_url})
    })

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@require_http_methods(['GET'])
def lab_details(request, lab_id):
    """ Display lab's details """

    loggedin_user_id = request.user.id
    is_admin = auth_utils.is_admin(request.user)
    is_pi = auth_utils.is_principal_investigator(loggedin_user_id, lab_id)
    if not is_admin and not is_pi:
        raise PermissionDenied

    # Check whether a lab exists or not
    lab = api.get_lab(lab_id)
    if not lab:
        raise Http404

    users_in_lab = api.get_users_in_lab(lab_id)
    for user in users_in_lab:
        if auth_utils.is_principal_investigator(user['id'], lab_id):
            user['isPI'] = True
        else:
            user['isPI'] = False

    redirect_url = '/areas/%d' % lab_id

    return render(request, 'lfs_lab_cert_tracker/lab_details.html', {
        'loggedin_user': request.user,
        'lab': api.get_lab(lab_id),
        'users_in_lab': users_in_lab,
        'users_missing_certs': api.get_users_missing_certs(lab_id),
        'users_expired_certs': api.get_users_expired_certs(lab_id),
        'required_certs': api.get_lab_certs(lab_id),
        'can_edit_user_lab': is_admin or is_pi,
        'can_edit_lab_cert': is_admin,
        'lab_user_form': UserLabForm(),
        'lab_cert_form': LabCertForm(initial={'redirect_url': redirect_url})
    })


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@auth_utils.admin_or_pi_only
@require_http_methods(['POST'])
def add_users_to_labs(request, lab_id):
    ''' Add users to labs '''
    if request.method == 'POST':
        username = request.POST.get('user')
        role = request.POST.get('role')

        user = api.get_user_by_username(username.strip())

        # Check whether a user exists or not
        if user != None:
            if api.create_user_lab(user.id, lab_id, role):
                valid_email = False
                valid_email_errors = []

                try:
                    validate_email(user.email)
                    valid_email = True
                except ValidationError as e:
                     valid_email_errors = e

                if valid_email:
                    messages.success(request, 'Success! {0} (CWL: {1}) added to this area.'.format(user.get_full_name(), user.username))
                else:
                    messages.warning(request, 'Warning! Added {0} successfully, but failed to send an email. ({1} is invalid)'.format(data['user'], user.email))
            else:
                messages.error(request, 'Error! Failed to add {0}. CWL already exists in this lab.'.format(user.username))
        else:
            messages.error(request, 'Error! Failed to add {0}. CWL does not exist in TRMS. Please go to a Users page then create the user by inputting the details before adding the user in the area.'.format(username))

    return HttpResponseRedirect( reverse('lab_details', args=[lab_id]) )

# Certificates

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@require_http_methods(['GET'])
def certs(request):
    """ Display all certificates """

    can_create_cert = auth_utils.is_admin(request.user)
    redirect_url = '/all-trainings/'

    cert_list = api.get_certs()

    # Pagination enables
    query = request.GET.get('q')
    if query:
        cert_list = Cert.objects.filter( Q(name__icontains=query) ).distinct()

    page = request.GET.get('page', 1)
    paginator = Paginator(cert_list, 50) # Set 50 certificates in a page
    try:
        certs = paginator.page(page)
    except PageNotAnInteger:
        certs = paginator.page(1)
    except EmptyPage:
        certs = paginator.page(paginator.num_pages)

    return render(request, 'lfs_lab_cert_tracker/certs.html', {
        'loggedin_user': request.user,
        'certs': certs,
        'total_certs': len(cert_list),
        'can_create_cert': can_create_cert,
        'cert_form': CertForm(initial={'redirect_url': redirect_url})
    })

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@require_http_methods(['POST'])
def edit_cert(request, cert_id):
    """ Edit a cert """

    if request.method == 'POST':
        cert = api.get_cert_object(cert_id)
        form = CertNameForm(request.POST, instance=cert)
        if form.is_valid():
            updated_cert = form.save()
            messages.success(request, 'Success! Training - {0} updated'.format(updated_cert.name))
        else:
            errors = form.errors.get_json_data()
            messages.error(request, 'An error occurred. Form is invalid. {0}'.format( api.get_error_messages(errors) ))

    return redirect('certs')


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
#@auth_utils.user_or_admin
@auth_utils.admin_or_pi_or_user
@require_http_methods(['GET'])
def download_user_cert(request, user_id=None, cert_id=None, filename=None):
    path = 'users/{0}/certificates/{1}/{2}'.format(user_id, cert_id, filename)
    return serve(request, path, document_root=settings.MEDIA_ROOT)

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@require_http_methods(['GET'])
def show_error(request, error_msg=''):
    return render(request, 'lfs_lab_cert_tracker/error.html', {
        'loggedin_user': request.user,
        'error_msg': error_msg
    })

# Exception handlers

def permission_denied(request, exception, template_name="403.html"):
    """ Exception handlder for permission denied """
    return render(request, '403.html', {
        'loggedin_user': request.user
    })

def page_not_found(request, exception, template_name="404.html"):
    """ Exception handlder for page not found """
    return render(request, '404.html', {
        'loggedin_user': request.user
    })


# for local testing

def local_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(username=request.POST['username'], password=request.POST['password'])
            if user is not None:
                DjangoLogin(request, user)
                return redirect('index')

    return render(request, 'lfs_lab_cert_tracker/local_login.html', { 'form': LoginForm() })
