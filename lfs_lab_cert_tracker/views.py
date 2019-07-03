from io import BytesIO

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.shortcuts import render, redirect
from django.views.static import serve
from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse
from cgi import escape
from xhtml2pdf import pisa

from lfs_lab_cert_tracker import api
from lfs_lab_cert_tracker import auth_utils
from lfs_lab_cert_tracker.forms import (LabForm, CertForm, UserForm,
        UserLabForm, LabCertForm, UserCertForm, SafetyWebForm, DeleteUserCertForm, LoginForm)

from lfs_lab_cert_tracker.models import UserCert
from django.db.models import Q
from django.contrib.auth import authenticate, login as DjangoLogin
from django.contrib.auth.models import User as AuthUser
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger



"""
HTTP endpoints, responsible for the frontend
"""

def my_login(request):
    auth_users = AuthUser.objects.all()
    #print(auth_users)
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            auth_user = AuthUser.objects.get(username=request.POST['username'])
            #auth_user = authenticate(request, email='michael.jordan@example.com', password='12')
            #print(auth_user)
            if auth_user is not None and request.POST['password'] is not None:
                #print(auth_user.password, request.POST['password'])
                DjangoLogin(request, auth_user)
                return redirect('index')

    context = {
        'form': LoginForm()
    }
    return render(request, 'lfs_lab_cert_tracker/my_login.html', context)


def login(request):
    return render(request, 'lfs_lab_cert_tracker/login.html')

def admin_login(request):
    return render(request, 'lfs_lab_cert_tracker/admin_login.html')

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@require_http_methods(['GET'])
def show_error(request, error_msg=''):
    loggedin_user_id = request.user.id
    return render(request,
            'lfs_lab_cert_tracker/error.html',
            {
                'loggedin_user': { 'username': api.get_user(loggedin_user_id) },
                'error_msg': error_msg
            }
    )

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@require_http_methods(['GET'])
def index(request):
    return redirect('/users/%d' % (request.user.id))

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@auth_utils.user_or_admin
@require_http_methods(['GET'])
def download_user_cert(request, user_id=None, cert_id=None, filename=None):
    #path = 'users/%d/certificates/%d' % (user_id, cert_id)
    #ADDED
    #print(filename)
    path = 'users/{0}/certificates/{1}/{2}'.format(user_id, cert_id, filename)
    return serve(request, path, document_root=settings.MEDIA_ROOT)

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@auth_utils.user_or_admin
@require_http_methods(['GET'])
def user_labs(request, user_id):
    loggedin_user_id = request.user.id
    user_lab_list = api.get_user_labs(loggedin_user_id)
    pi_user_lab_list = api.get_user_labs(loggedin_user_id, is_principal_investigator=True)

    return render(request,
            'lfs_lab_cert_tracker/user_labs.html',
            {
                'user_id': loggedin_user_id,
                'user_lab_list': user_lab_list,
                'pi_user_lab_list': pi_user_lab_list,
                'loggedin_user': { 'username': api.get_user(loggedin_user_id) }
            }
    )

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@auth_utils.user_or_admin
@require_http_methods(['GET'])
def user_certs(request, user_id):
    loggedin_user_id = request.user.id
    redirect_url = '/users/%d/certificates/' % loggedin_user_id
    return render(request,
             'lfs_lab_cert_tracker/user_certs.html',
             {
                'loggedin_user': { 'username': api.get_user(loggedin_user_id) },
                 'user_id': loggedin_user_id,
                 'user_cert_list': api.get_user_certs(loggedin_user_id),
                 'missing_cert_list': api.get_missing_certs(loggedin_user_id),
                 'expired_cert_list': api.get_expired_certs(loggedin_user_id),
                 'user_cert_form': UserCertForm(initial={'user': loggedin_user_id, 'redirect_url': redirect_url})
             }
     )


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@require_http_methods(['GET'])
def labs(request):
    is_admin = auth_utils.is_admin(request.user)
    redirect_url = '/labs/'

    lab_list = api.get_labs()
    total_labs = len(lab_list)
    query = request.GET.get('q')

    if query:
        lab_list = Lab.objects.filter( Q(name__icontains=query) ).distinct()

    page = request.GET.get('page', 1)
    paginator = Paginator(lab_list, 20)
    try:
        labs = paginator.page(page)
    except PageNotAnInteger:
        labs = paginator.page(1)
    except EmptyPage:
        labs = paginator.page(paginator.num_pages)

    return render(request,
        'lfs_lab_cert_tracker/labs.html',
        {
            'labs': labs,
            'total_labs': total_labs,
            'can_create_lab': is_admin,
            'lab_form': LabForm(initial={'redirect_url': redirect_url}),
            'loggedin_user': { 'username': api.get_user(request.user.id) }
        }
    )

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@require_http_methods(['GET'])
def certs(request):
    can_create_cert = auth_utils.is_admin(request.user)
    redirect_url = '/certificates/'

    cert_list = api.get_certs()
    total_certs = len(cert_list)
    query = request.GET.get('q')

    if query:
        cert_list = Cert.objects.filter( Q(name__icontains=query) ).distinct()

    page = request.GET.get('page', 1)
    paginator = Paginator(cert_list, 20)
    try:
        certs = paginator.page(page)
    except PageNotAnInteger:
        certs = paginator.page(1)
    except EmptyPage:
        certs = paginator.page(paginator.num_pages)

    return render(request,
        'lfs_lab_cert_tracker/certs.html',
        {
            'certs': certs,
            'total_certs': total_certs,
            'can_create_cert': can_create_cert,
            'cert_form': CertForm(initial={'redirect_url': redirect_url}),
            'loggedin_user': { 'username': api.get_user(request.user.id) }
        }
    )


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@require_http_methods(['GET'])
def users(request):
    is_admin = auth_utils.is_admin(request.user)

    if not is_admin:
        raise PermissionDenied

    redirect_url = '/users/'

    user_list = api.get_users()
    total_users = len(user_list)
    query = request.GET.get('q')

    if query:
        user_list = AuthUser.objects.filter(
            Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
        ).distinct()

    page = request.GET.get('page', 1)
    paginator = Paginator(user_list, 10)
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)

    return render(request,
        'lfs_lab_cert_tracker/users.html',
        {
            'users': users,
            'total_users': total_users,
            'user_form': UserForm(initial={'redirect_url': redirect_url}),
            'loggedin_user': { 'username': api.get_user(request.user.id) }
        }
    )

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@require_http_methods(['GET'])
def lab_details(request, lab_id):
    request_user_id = request.user.id
    is_admin = auth_utils.is_admin(request.user)
    is_pi = auth_utils.is_principal_investigator(request_user_id, lab_id)
    if not is_admin and not is_pi:
        raise PermissionDenied

    lab = api.get_lab(lab_id)
    users_in_lab = api.get_users_in_lab(lab_id)
    for user in users_in_lab:
        if auth_utils.is_principal_investigator(user['id'], lab_id):
            user['isPI'] = True
        else:
            user['isPI'] = False

    users_missing_certs = api.get_users_missing_certs(lab_id)
    required_certs = api.get_lab_certs(lab_id)
    redirect_url = '/labs/%d' % lab_id

    return render(request,
            'lfs_lab_cert_tracker/lab_details.html',
            {
                'lab': lab,
                'users_in_lab': users_in_lab,
                'users_missing_certs': users_missing_certs,
                'required_certs': required_certs,
                'can_edit_user_lab': is_admin or is_pi,
                'can_edit_lab_cert': is_admin or is_pi,
                'lab_cert_form': LabCertForm(initial={'redirect_url': redirect_url}),
                'lab_user_form': UserLabForm(initial={'redirect_url': redirect_url}),
                'loggedin_user': { 'username': api.get_user(request.user.id) }
            }
    )

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@auth_utils.user_or_admin
@require_http_methods(['GET'])
def user_cert_details(request, user_id=None, cert_id=None):
    loggedin_user_id = request.user.id
    # Retrieve information about the user cert
    user_cert = api.get_user_cert(user_id, cert_id)
    redirect_url = '/users/%d/certificates/' % loggedin_user_id
    delete_user_cert_form = DeleteUserCertForm(initial={'redirect_url': redirect_url})

    return render(request,
            'lfs_lab_cert_tracker/user_cert_details.html',
            {
                'loggedin_user': { 'username': api.get_user(request.user.id) },
                'user_id': user_id,
                'user_cert': user_cert,
                'delete_user_cert_form': delete_user_cert_form
            }
    )

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@auth_utils.user_or_admin
@require_http_methods(['GET'])
def user_details(request, user_id=None):
    app_user = api.get_user(user_id)
    if app_user is None:
        raise PermissionDenied

    user_lab_list = api.get_user_labs(user_id)
    user_cert_list = api.get_user_certs(user_id)
    missing_cert_list = api.get_missing_certs(user_id)
    expired_cert_list = api.get_expired_certs(user_id)
    pi_user_lab_list = api.get_user_labs(user_id, is_principal_investigator=True)

    return render(request,
            'lfs_lab_cert_tracker/user_details.html',
            {
                'user_lab_list': user_lab_list,
                'pi_user_lab_list': pi_user_lab_list,
                'user_cert_list': user_cert_list,
                'missing_cert_list': missing_cert_list,
                'expired_cert_list': expired_cert_list,
                'app_user': app_user,
                'loggedin_user': { 'username': api.get_user(request.user.id) }
            }
    )

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@auth_utils.user_or_admin
@require_http_methods(['GET'])
def user_report(request, user_id=None):
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

    return render_to_pdf('lfs_lab_cert_tracker/user_report.html',
            {
                'user_cert_list': user_cert_list,
                'app_user': app_user,
                'user_labs': user_labs,
            }
    )

def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    context = Context(context_dict)
    html  = template.render(context_dict)
    response = BytesIO()

    pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), response)
    if not pdf.err:
        return HttpResponse(response.getvalue(), content_type='application/pdf')
    return HttpResponse('Encountered errors <pre>%s</pre>' % escape(html))
