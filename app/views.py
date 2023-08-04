import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from django.shortcuts import render, redirect
from django.views.static import serve
from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.urls import reverse
from django.core.validators import validate_email
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.contrib.auth.models import User
from django.core.exceptions import SuspiciousOperation
from collections import defaultdict

from io import BytesIO
from django.http import FileResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, ListFlowable, ListItem
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# from cgi import escape
from html import escape # >= python 3.8
from xhtml2pdf import pisa
from datetime import datetime

from .accesses import *
from .forms import *
from .utils import Api
from . import api
from lfs_lab_cert_tracker.models import UserInactive, Lab, Cert, UserLab, UserCert, UserApiCerts


NUM_PER_PAGE = 20

uApi = Api()

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@require_http_methods(['GET'])
def index(request):
    full_name = request.META[settings.SHIB_ATTR_MAP['full_name']] if settings.SHIB_ATTR_MAP['full_name'] in request.META else None
    last_name = request.META[settings.SHIB_ATTR_MAP['last_name']] if settings.SHIB_ATTR_MAP['last_name'] in request.META else None
    email = request.META[settings.SHIB_ATTR_MAP['email']] if settings.SHIB_ATTR_MAP['email'] in request.META else None
    username = request.META[settings.SHIB_ATTR_MAP['username']] if settings.SHIB_ATTR_MAP['username'] in request.META else None

    if not username:
        raise SuspiciousOperation

    first_name = None
    if full_name:
        first_name = full_name.split(last_name)[0].strip()

    # Update user information if it's None
    update_fields = []
    if not request.user.first_name and first_name:
        request.user.first_name = first_name
        update_fields.append('first_name')
    
    if not request.user.last_name and last_name:
        request.user.last_name = last_name
        update_fields.append('last_name')
        
    if not request.user.email and email:
        request.user.email = email
        update_fields.append('email')
    
    if len(update_fields) > 0:
        request.user.save(update_fields=update_fields)

    return HttpResponseRedirect(reverse('app:user_details', args=[request.user.id]))


# Users - classes

@method_decorator([never_cache, login_required, access_admin_only], name='dispatch')
class AllUsersView(View):
    """ Display all users """

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        # if session has next value, delete it
        if request.session.get('next'):
            del request.session['next']


        # Pagination enables
        query = request.GET.get('q')
        if query:
            user_list = User.objects.filter(
                Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
            ).order_by('id').distinct()
        else:
            user_list = uApi.get_users()

        page = request.GET.get('page', 1)
        paginator = Paginator(user_list, NUM_PER_PAGE)

        try:
            users = paginator.page(page)
        except PageNotAnInteger:
            users = paginator.page(1)
        except EmptyPage:
            users = paginator.page(paginator.num_pages)

        users = uApi.add_inactive_users(users)

        areas = uApi.get_areas()

        return render(request, 'app/users/all_users.html', {
            'users': users,
            'total_users': len(user_list),
            'areas': uApi.add_users_to_areas(areas, users),
            'roles': {'LAB_USER': 0, 'PI': 1}
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):

        # Edit a user
        user = uApi.get_user(request.POST.get('user'))
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            if form.save():
                messages.success(request, 'Success! {0} updated.'.format(user.get_full_name()))
            else:
                messages.error(request, 'Error! Failed to update {0}.'.format(user.get_full_name()))
        else:
            errors = form.errors.get_json_data()
            messages.error(request, 'Error! Form is invalid. {0}'.format( uApi.get_error_messages(errors) ))

        return HttpResponseRedirect( request.POST.get('next') )
    

@method_decorator([never_cache, login_required, access_admin_only], name='dispatch')
class UserCertificatesView(View):
    """ Display all users' certificates grabbed from API """

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        # Retrieve all UserApiCerts objects
        user_api_certs = UserApiCerts.objects.all()

        # Create a defaultdict to store the user certificates
        user_certificates = defaultdict(list)

        # Iterate over UserApiCerts objects and group them by user
        for cert in user_api_certs:
            user_certificates[cert.user].append(cert)

        # Convert defaultdict to a regular dictionary
        user_certificates_dict = dict(user_certificates)
        
        # Get a list of unique users
        users = list(user_certificates_dict.keys())

        if request.session.get('next'):
            del request.session['next']

        # Pagination
        page = request.GET.get('page', 1)
        paginator = Paginator(users, NUM_PER_PAGE)

        try:
            users_paginated = paginator.page(page)
        except PageNotAnInteger:
            users_paginated = paginator.page(1)
        except EmptyPage:
            users_paginated = paginator.page(paginator.num_pages)

        return render(request, 'app/users/user_certificates.html', {
            'user_certificates_dict': user_certificates_dict,
            'users_paginated': users_paginated,
            'total_users': len(users),
        })


@method_decorator([never_cache, login_required, access_admin_only], name='dispatch')
class UserReportMissingTrainingsView(View):
    """ Display a user report for missing trainings """

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        user_list = uApi.get_users()

        # Pagination enables
        query = request.GET.get('q')
        if query:
            user_list = user_list.filter(
                Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
            ).order_by('id').distinct()

        user_list = api.get_users_with_missing_certs(user_list)

        page = request.GET.get('page', 1)
        paginator = Paginator(user_list, NUM_PER_PAGE)

        try:
            users = paginator.page(page)
        except PageNotAnInteger:
            users = paginator.page(1)
        except EmptyPage:
            users = paginator.page(paginator.num_pages)

        return render(request, 'app/users/user_report_missing_trainings.html', {
            'users': users,
            'total_users': len(user_list)
        })


@method_decorator([never_cache, login_required, access_admin_only], name='dispatch')
class NewUserView(View):
    """ Create a new user """

    form_class = UserForm

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        return render(request, 'app/users/new_user.html', {
            'user_form': self.form_class(),
            'last_ten_users': User.objects.all().order_by('-date_joined')[:15]
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save()
            if user:
                if request.POST.get('send_email') == 'yes':
                    email_error = None
                    try:
                        validate_email(user.email)
                    except ValidationError as e:
                         email_error = e

                    if email_error is None:
                        sent = uApi.send_notification(user)
                        if sent:
                            messages.success(request, 'Success! {0} created and sent an email.'.format(user.get_full_name()))
                        else:
                            messages.warning(request, 'Warning! {0} created, but failed to send an email due to {1}'.format(user.get_full_name(), sent.error))
                else:
                    messages.success(request, 'Success! {0} created.'.format(user.get_full_name()))
            else:
                messages.error(request, 'Error! Failed to create {0}. Please check your CWL.'.format(user.get_full_name()))
        else:
            errors = form.errors.get_json_data()
            messages.error(request, 'Error! Form is invalid. {0}'.format( uApi.get_error_messages(errors) ) )

        return redirect('app:new_user')


@method_decorator([never_cache, login_required, access_loggedin_user_pi_admin], name='dispatch')
class UserDetailsView(View):
    """ View user details """

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        user_id = kwargs['user_id']

        if request.user.id != user_id:

            # Add next string to session
            if request.GET.get('next'):
                next = request.get_full_path().split('next=')
                request.session['next'] = next[1]

        viewing = {}
        if request.user.id != user_id and request.session.get('next'):
            viewing = uApi.get_viewing(request.session.get('next'))

        return render(request, 'app/users/user_details.html', {
            'app_user': uApi.get_user(kwargs['user_id']),
            'user_lab_list': api.get_user_labs(user_id),
            'pi_user_lab_list': api.get_user_labs(user_id, is_principal_investigator=True),
            'user_certs': api.get_user_certs_without_duplicates(api.get_user_404(user_id)),
            'missing_cert_list': api.get_missing_certs(user_id),
            'expired_cert_list': api.get_expired_certs(user_id),
            'welcome_message': uApi.welcome_message(),
            'viewing': viewing
        })


@method_decorator([never_cache, login_required, access_loggedin_user_admin], name='dispatch')
class UserAreasView(View):
    """ Display user's areas """

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        return render(request, 'app/areas/user_areas.html', {
            'user_lab_list': api.get_user_labs(request.user.id),
            'pi_user_lab_list': api.get_user_labs(request.user.id, is_principal_investigator=True)
        })


@method_decorator([never_cache, login_required, access_loggedin_user_pi_admin], name='dispatch')
class UserTrainingsView(View):
    """ Display all training records of a user """

    form_class = UserTrainingForm

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        user_id = kwargs['user_id']
        app_user = uApi.get_user(user_id)

        viewing = {}
        if request.user.id != user_id and request.session.get('next'):
            viewing = uApi.get_viewing(request.session.get('next'))

        return render(request, 'app/trainings/user_trainings.html', {
            'app_user': app_user,
            'user_cert_list': api.get_user_certs(user_id),
            'missing_cert_list': api.get_missing_certs(user_id),
            'expired_cert_list': api.get_expired_certs(user_id),
            'form': self.form_class(initial={ 'user': user_id }),
            'viewing': viewing
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):

        # Add a training record
        user_id = request.POST.get('user')
        form = self.form_class(request.POST, request.FILES)

        # Whether form is valid or not
        if form.is_valid():
            data = request.POST
            files = request.FILES
            cert = api.get_cert(data['cert'])

            year = int(data['completion_date_year'])
            month = int(data['completion_date_month'])
            day = int(data['completion_date_day'])

            completion_date = datetime(year=year, month=month, day=day)

            # Calculate a expiry year
            expiry_year = year + int(cert['expiry_in_years'])
            expiry_date = datetime(year=expiry_year, month=month, day=day)

            result = api.update_or_create_user_cert(data['user'], data['cert'], files['cert_file'], completion_date, expiry_date)

            # Whether user's certficiate is created successfully or not
            if result:
                uApi.remove_missing_cert(user_id, cert['id'])
                messages.success(request, 'Success! {0} added.'.format(cert['name']))
                res = { 'user_id': user_id, 'cert_id': result['cert'] }
            else:
                messages.error(request, "Error! Failed to add a training. Check if your training already exists")
        else:
            errors_data = form.errors.get_json_data()
            error_message = 'Please check your inputs.'

            for key in errors_data.keys():
                error_code = errors_data[key][0]['code']

                if error_code == 'unique_together':
                    error_message = "The certificate already exists. If you wish to update a new training, please delete your old training first."

                elif error_code == 'invalid_extension':
                    error_message = errors_data[key][0]['message']

                elif error_code == 'file_size_limit':
                    error_message = errors_data[key][0]['message']

                elif error_code == 'max_length':
                    error_message = errors_data[key][0]['message']

            messages.error(request, "Error! Failed to add your training. {0}".format(error_message))

        return HttpResponseRedirect(reverse('app:user_trainings', args=[user_id]))


@method_decorator([never_cache, login_required, access_loggedin_user_pi_admin], name='dispatch')
class UserTrainingDetailsView(View):
    """ Display details of a training record of a user """

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        user_id = kwargs['user_id']
        training_id = kwargs['training_id']

        viewing = {}
        if request.user.id != user_id and request.session.get('next'):
            viewing = uApi.get_viewing(request.session.get('next'))

        user_certs = api.get_user_certs_specific_404(user_id, training_id)
        no_expiry_date = False
        user_cert = user_certs.first()
        if user_cert.completion_date == user_cert.expiry_date:
            no_expiry_date = True

        return render(request, 'app/trainings/user_training_details.html', {
            'app_user': uApi.get_user(user_id),
            'user_certs': user_certs,
            'no_expiry_date': no_expiry_date,
            'viewing': viewing
        })


# Users - functions

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_loggedin_user_pi_admin
@require_http_methods(['GET'])
def user_report(request, user_id):
    """ Download user's report as PDF """

    app_user = uApi.get_user(user_id)

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

    for uc in user_cert_list:
        no_expiry_date = False
        if uc['completion_date'] == uc['expiry_date']:
            no_expiry_date = True
        uc['no_expiry_date'] = no_expiry_date

    return render_to_pdf('app/users/user_report.html', {
        'app_user': app_user,
        'user_labs': user_labs,
        'user_cert_list': user_cert_list
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


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['GET'])
def download_user_report_missing_trainings(request):
    """Download a user report for missing trainings """

    users = uApi.get_users()

    # Find users who have missing certs
    users_in_missing_training = list(api.get_users_with_missing_certs(users))

    # Generate PDF using ReportLab
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0, leftMargin=0, topMargin=0, bottomMargin=0)

    # Header
    styles = getSampleStyleSheet()

    # Modify the Heading1 style for the main header
    styles['Heading1'].alignment = 1  # 1 for center alignment
    styles['Heading1'].fontSize = 16

    # Modify the Heading2 style for the table headers
    styles['Heading2'].alignment = 1 
    styles['Heading2'].fontSize = 12 

    header = Paragraph("User Report (Total: {})".format(len(users_in_missing_training)), styles['Heading1'])
    doc.build([header])

    # Table data
    data = [[Paragraph('ID', styles['Heading2']), 
             Paragraph('Full Name', styles['Heading2']),
             Paragraph('CWL', styles['Heading2']),
             Paragraph('Number of Missing Trainings', styles['Heading2']),
             Paragraph('Missing Training Records', styles['Heading2'])]]

    for user in users_in_missing_training:
        row = [
            Paragraph(str(user.id), styles['BodyText']),
            Paragraph(user.get_full_name(), styles['BodyText']),
            Paragraph(user.username, styles['BodyText']),
            Paragraph(str(user.missing_certs.count()), styles['BodyText']),
        ]
        missing_certs = [ListItem(Paragraph(training.cert.name, styles['BodyText'])) for training in user.missing_certs.all()]
        certs_list = ListFlowable(missing_certs, bulletType='bullet', leftIndent=10)
        row.append(certs_list)
        data.append(row)


    # Set column widths
    col_widths = [doc.width * 0.1, doc.width * 0.3, doc.width * 0.2, doc.width * 0.2, doc.width * 0.2]

    # Table style
    table_style = TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
    ])

    # Create table
    table = Table(data, colWidths=col_widths)
    table.setStyle(table_style)

    # Add table to the document
    doc.build([header, table])

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename='user_report_missing_trainings.pdf')


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def delete_user(request):
    """ Delete a user """

    user = uApi.get_user(request.POST.get('user'))
    if user.delete():
        messages.success(request, 'Success! {0} deleted.'.format(user.get_full_name()))
    else:
        messages.error(request, 'Error! Failed to delete {0}.'.format(user.get_full_name()))

    return HttpResponseRedirect(request.POST.get('next'))


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def switch_admin(request):
    """ Switch a user to Admin or not Admin """

    user = uApi.get_user(request.POST.get('user'))

    user.is_superuser = not user.is_superuser
    user.save(update_fields=['is_superuser'])

    if user.is_superuser:
        messages.success(request, 'Success! Granted administrator privileges to {0}.'.format(user.get_full_name()))
    else:
        messages.success(request, 'Success! Revoked administrator privileges of {0}.'.format(user.get_full_name()))

    return HttpResponseRedirect(request.POST.get('next'))


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def switch_inactive(request):
    """ Switch a user to Active or Inactive """

    user = uApi.get_user(request.POST.get('user'))

    if user.is_active:
        UserInactive.objects.create(user_id=user.id, inactive_date=datetime.now())
    else:
        UserInactive.objects.get(user_id=user.id).delete()

    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])

    if user.is_active:
        messages.success(request, 'Success! {0} is now ACTIVE.'.format(user.get_full_name()))
    else:
        messages.success(request, 'Success! {0} is now INACTIVE.'.format(user.get_full_name()))

    return HttpResponseRedirect(request.POST.get('next'))


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def assign_user_areas(request):
    """ Assign user's areas """

    user = uApi.get_user(request.POST.get('user'))

    # delete all or not
    if len(request.POST.getlist('areas[]')) == 0:
        all_userlab = user.userlab_set.all()

        if len(all_userlab) > 0:
            report = uApi.update_or_create_areas_to_user(user, [])
            if all_userlab.delete():
                return JsonResponse({ 'status': 'success', 'message': "Success! {0}'s all areas have deleted.".format(user.get_full_name()) })
            else:
                return JsonResponse({ 'status': 'error', 'message': 'Error! Failed to delete all areas.' })
        else:
            return JsonResponse({ 'status': 'warning', 'message': 'Warning! Nothing has changed.' })

    else:
        areas = request.POST.getlist('areas[]')
        user = uApi.get_user(request.POST.get('user'))
        all_userlab = user.userlab_set.all()

        report = uApi.update_or_create_areas_to_user(user, areas)
        message = ''

        if len(report['updated']) > 0:
            message += '<li>Changed: ' + ', '.join(report['updated']) + '</li>'
        if len(report['created']) > 0:
            message += '<li>Added: ' + ', '.join(report['created']) + '</li>'
        if len(report['deleted']) > 0:
            message += '<li>Deleted: ' + ', '.join(report['deleted']) + '</li>'

        if len(message) == 0:
            return JsonResponse({ 'status': 'warning', 'message': 'Warning! Nothing has changed.' })
        else:
            return JsonResponse({ 'status': 'success', 'message': 'Success! ' + user.get_full_name() + "'s Areas have changed. Please see the following status: <ul class='mb-0'>" + message + '</ul>' })

    return JsonResponse({ 'status': 'error', 'message': 'Error! Something went wrong.' })


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_loggedin_user_pi_admin
@require_http_methods(['POST'])
def read_welcome_message(request, user_id):
    """ Read a welcome message """

    if request.POST.get('read_welcome_message') == 'true':
        request.session['is_first_time'] = False
        return JsonResponse({ 'status': 'success', 'message': 'Success! A user read a welcome message.' })

    return JsonResponse({ 'status': 'error', 'message': 'Error! Something went wrong while reading a welcome message.' })


# Areas - classes

@method_decorator([never_cache, login_required, access_admin_only], name='dispatch')
class AllAreasView(View):
    """ Display all areas """

    form_class = AreaForm

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        area_list = uApi.get_areas()

        # Pagination enables
        query = request.GET.get('q')
        if query:
            area_list = Lab.objects.filter( Q(name__icontains=query) ).distinct()

        page = request.GET.get('page', 1)
        paginator = Paginator(area_list, NUM_PER_PAGE)

        try:
            areas = paginator.page(page)
        except PageNotAnInteger:
            areas = paginator.page(1)
        except EmptyPage:
            areas = paginator.page(paginator.num_pages)

        # Add a number of users in each area
        for area in areas:
            area.num_users = area.userlab_set.count()

        return render(request, 'app/areas/all_areas.html', {
            'areas': areas,
            'total_areas': len(area_list),
            'form': self.form_class()
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):

        # Create a new area
        form = self.form_class(request.POST)
        if form.is_valid():
            lab = form.save()
            if lab:
                messages.success(request, 'Success! {0} created.'.format(lab.name))
            else:
                messages.error(request, 'Error! Failed to create {0}.'.format(lab.name))
        else:
            errors = form.errors.get_json_data()
            messages.error(request, 'Error! Form is invalid. {0}'.format(uApi.get_error_messages(errors)))

        return redirect('app:all_areas')


@method_decorator([never_cache, login_required, access_pi_admin], name='dispatch')
class AreaDetailsView(View):
    """ Display all areas """

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        # if session has next value, delete it
        if request.session.get('next'):
            del request.session['next']

        area_id = kwargs['area_id']

        area = uApi.get_area(area_id)

        required_trainings = []
        for labcert in area.labcert_set.all():
            required_trainings.append(labcert.cert)


        userlab_set = area.userlab_set.all()
        query = request.GET.get('q')
        if query:
            userlab_set = userlab_set.filter(
                Q(user__username__icontains=query) | Q(user__first_name__icontains=query) | Q(user__last_name__icontains=query)
            ).order_by('id').distinct()

        page = request.GET.get('page', 1)
        paginator = Paginator(userlab_set, NUM_PER_PAGE)

        try:
            userlabs = paginator.page(page)
        except PageNotAnInteger:
            userlabs = paginator.page(1)
        except EmptyPage:
            userlabs = paginator.page(paginator.num_pages)

        users_in_area = []
        for userlab in userlabs: 
            user = userlab.user
            if uApi.is_pi_in_area(user.id, area_id): user.is_pi = True
            else: user.is_pi = False
            users_in_area.append(user)

        is_pi = uApi.is_pi_in_area(request.user.id, area_id)

        # Add lab missing cert and lab expired cert data to user
        api.get_users_missing_certs(area_id, userlabs)
        api.get_users_expired_certs(area_id, userlabs)

        return render(request, 'app/areas/area_details.html', {
            'area': area,
            'required_trainings': required_trainings,
            'users_in_area': users_in_area,
            'userlabs': userlabs,
            'total_users': len(userlab_set),
            'is_admin': request.user.is_superuser,
            'is_pi': is_pi,
            'user_area_form': UserAreaForm(initial={ 'lab': area.id }),
            'area_training_form': AreaTrainingForm(initial={ 'lab': area.id })
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        """ Add a user to an area """

        username = request.POST.get('user')
        role = request.POST.get('role')
        area_id = request.POST.get('lab')

        found_user = User.objects.filter(username=username)

        # Check whether a user exists or not
        if found_user.exists():
            user = found_user.first()
            found_userlab = UserLab.objects.filter( Q(user_id=user.id) & Q(lab_id=area_id) )

            if found_userlab.exists() == False:
                userlab = UserLab.objects.create(user_id=user.id, lab_id=area_id, role=role)
                valid_email = False
                valid_email_error = None

                uApi.add_missing_certificates_for_added_user(user, area_id)

                try:
                    validate_email(user.email)
                    valid_email = True
                except ValidationError as e:
                     valid_email_error = e

                if valid_email:
                    messages.success(request, 'Success! {0} (CWL: {1}) added to this area.'.format(user.get_full_name(), user.username))
                else:
                    messages.warning(request, 'Warning! Added {0} successfully, but failed to send an email. ({1} is invalid) {2}'.format(user.get_full_name(), user.email, valid_email_error))
            else:
                messages.error(request, 'Error! Failed to add {0}. CWL already exists in this area.'.format(user.username))
        else:
            messages.error(request, 'Error! Failed to add {0}. CWL does not exist in TRMS. Please go to a Users page then create the user by inputting the details before adding the user in the area.'.format(username))

        return HttpResponseRedirect(reverse('app:area_details', args=[area_id]))


# Areas - functions

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def add_training_area(request):
    """ Add a training to an area """

    area_id = request.POST.get('lab', None)
    training_id = request.POST.get('cert', None)

    if area_id == None:
        messages.error(request, 'Error! Something went wrong. Area is required.')
        return redirect('app:all_areas')

    if training_id == None:
        messages.error(request, 'Error! Something went wrong. Training is required.')
        return HttpResponseRedirect(reverse('app:area_details', args=[area_id]))

    area = uApi.get_area(area_id)
    training = uApi.get_training(training_id)

    labcert = uApi.get_labcert(request.POST.get('lab'), request.POST.get('cert'))

    if labcert == None:
        form = AreaTrainingForm(request.POST, instance=labcert)
        if form.is_valid():
            new_labcert = form.save()
            messages.success(request, 'Success! {0} added.'.format(new_labcert.cert.name))
            uApi.add_missing_trainings(area_id, new_labcert.cert)
        else:
            errors = form.errors.get_json_data()
            messages.error(request, 'Error! Form is invalid. {0}'.format( uApi.get_error_messages(errors) ))
    else:
        messages.error(request, 'Error! Failed to add Training. This training has already existed.'.format(labcert.cert.name))


    return HttpResponseRedirect(reverse('app:area_details', args=[area_id]))


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def delete_training_in_area(request):
    """ Delete a required training in the area """

    area_id = request.POST.get('area', None)
    training_id = request.POST.get('training', None)

    if area_id == None:
        messages.error(request, 'Error! Something went wrong. Area is required.')
        return redirect('app:all_areas')

    if training_id == None:
        messages.error(request, 'Error! Something went wrong. Training is required.')
        return HttpResponseRedirect(reverse('app:area_details', args=[area_id]))

    area = uApi.get_area(area_id)
    training = uApi.get_training(training_id)

    labcert = uApi.get_labcert(area_id, training_id)

    if labcert == None:
        messages.error(request, 'Error! {0} does not exist in this area.'.format(training.name))
    else:
        uApi.remove_missing_trainings_for_deleted_labcert(area_id, labcert.cert)
        if labcert.delete():
            messages.success(request, 'Success! {0} deleted.'.format(labcert.cert.name))
        else:
            messages.error(request, 'Error! Failed to delete {0}.'.format(labcert.cert.name))

    return HttpResponseRedirect(reverse('app:area_details', args=[area_id]))


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def edit_area(request):
    """ Update the name of area """

    area = uApi.get_area(request.POST.get('area'))

    form = AreaForm(request.POST, instance=area)
    if form.is_valid():
        updated_area = form.save()
        if updated_area:
            messages.success(request, 'Success! {0} updated.'.format(updated_area.name))
        else:
            messages.error(request, 'Error! Failed to update {0}.'.format(area.name))
    else:
        errors = form.errors.get_json_data()
        messages.error(request, 'Error! Form is invalid. {0}'.format(uApi.get_error_messages(errors)))

    return redirect('app:all_areas')


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def delete_area(request):
    """ Delete an area """

    area = uApi.get_area(request.POST.get('area'))
    uApi.remove_missing_trainings_for_users_in_area(area)
    if area.delete():
        messages.success(request, 'Success! {0} deleted.'.format(area.name))
    else:
        messages.error(request, 'Error! Failed to delete {0}.'.format(area.name))

    return redirect('app:all_areas')


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_pi_admin
@require_http_methods(['POST'])
def switch_user_role_in_area(request, area_id):
    """ Switch a user's role in the area """

    user_id = request.POST.get('user', None)
    area_id = request.POST.get('area', None)

    if user_id == None:
        messages.error(request, 'Error! Something went wrong. User is required.')
        return HttpResponseRedirect(reverse('app:area_details', args=[area_id]))

    if area_id == None:
        messages.error(request, 'Error! Something went wrong. Area is required.')
        return redirect('app:all_areas')

    user = uApi.get_user(user_id)
    area = uApi.get_area(area_id)

    userlab = uApi.get_userlab(user_id, area_id)

    if userlab == None:
        messages.error(request, 'Error! A user or an area data does not exist.')
    else:
        role = ''
        prev_role = userlab.role

        if userlab.role == UserLab.LAB_USER:
            userlab.role = UserLab.PRINCIPAL_INVESTIGATOR
            role = 'Supervisor'
        else:
            userlab.role = UserLab.LAB_USER
            role = 'User'

        userlab.save(update_fields=['role'])

        if userlab.role != prev_role:
            messages.success(request, 'Success! {0} is now a {1}.'.format(user.get_full_name(), role))
        else:
            messages.error(request, 'Error! Failed to switch a role of {0}.'.format(user.get_full_name()))

    return HttpResponseRedirect(reverse('app:area_details', args=[area_id]))


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_pi_admin
@require_http_methods(['POST'])
def delete_user_in_area(request, area_id):
    """ Delete a user in the area """

    user_id = request.POST.get('user', None)
    area_id = request.POST.get('area', None)

    if user_id == None:
        messages.error(request, 'Error! Something went wrong. User is required.')
        return HttpResponseRedirect(reverse('app:area_details', args=[area_id]))

    if area_id == None:
        messages.error(request, 'Error! Something went wrong. Area is required.')
        return redirect('app:all_areas')

    user = uApi.get_user(user_id)
    area = uApi.get_area(area_id)

    userlab = uApi.get_userlab(user_id, area_id)

    if userlab == None:
        messages.error(request, 'Error! A user or an area data does not exist.')
    else:
        uApi.remove_user_from_area_update_missing(area, user)
        if userlab.delete():
            messages.success(request, 'Success! {0} deleted.'.format(user.get_full_name()))
        else:
            messages.error(request, 'Error! Failed to delete {0}.'.format(user.get_full_name()))

    return HttpResponseRedirect(reverse('app:area_details', args=[area_id]))


# Trainings - classes

@method_decorator([never_cache, login_required, access_admin_only], name='dispatch')
class AllTrainingsView(View):
    """ Display all training records of a user """

    form_class = TrainingForm

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        training_list = uApi.get_trainings()

        # Pagination enables
        query = request.GET.get('q')
        if query:
            training_list = Cert.objects.filter( Q(name__icontains=query) ).distinct()

        page = request.GET.get('page', 1)
        paginator = Paginator(training_list, NUM_PER_PAGE)

        try:
            trainings = paginator.page(page)
        except PageNotAnInteger:
            trainings = paginator.page(1)
        except EmptyPage:
            trainings = paginator.page(paginator.num_pages)

        return render(request, 'app/trainings/all_trainings.html', {
            'trainings': trainings,
            'total_trainings': len(training_list),
            'form': self.form_class()
        })


    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):

        # Create a new training

        form = self.form_class(request.POST)
        if form.is_valid():
            cert = form.save()
            if cert:
                messages.success(request, 'Success! {0} created.'.format(cert.name))
            else:
                messages.error(request, 'Error! Failed to create {0}. This training has already existed.'.format(cert.name))
        else:
            errors = form.errors.get_json_data()
            messages.error(request, 'Error! Form is invalid. {0}'.format(uApi.get_error_messages(errors)))

        return redirect('app:all_trainings')


# Trainings - functions

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def edit_training(request):
    """ Edit a training """

    training = uApi.get_training( request.POST.get('training') )
    new_expiry_in_years = int(request.POST.get('expiry_in_years')) - training.expiry_in_years

    form = TrainingForm(request.POST, instance=training)
    if form.is_valid():
        updated_training = form.save()
        usercerts = UserCert.objects.filter(cert_id=training.id)

        objs = []
        if usercerts.count() > 0 and new_expiry_in_years != 0:
            for usercert in usercerts:
                usercert.expiry_date = datetime(usercert.expiry_date.year + new_expiry_in_years, usercert.expiry_date.month, usercert.expiry_date.day)
                objs.append(usercert)

            UserCert.objects.bulk_update(objs, ['expiry_date'])
            messages.success(request, 'Success! {0} training and {1} user training record(s) updated'.format(updated_training.name, len(objs)))
        else:
            messages.success(request, 'Success! {0} training updated'.format(updated_training.name))
    else:
        errors = form.errors.get_json_data()
        messages.error(request, 'An error occurred. Form is invalid. {0}'.format( uApi.get_error_messages(errors) ))

    return redirect('app:all_trainings')


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def delete_training(request):
    """ Delete a training """

    training = uApi.get_training(request.POST.get('training'))

    if training.delete():
        messages.success(request, 'Success! {0} deleted.'.format(training.name))
    else:
        messages.error(request, 'Error! Failed to delete {0}.'.format(training.name))

    return redirect('app:all_trainings')


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_loggedin_user_admin
@require_http_methods(['POST'])
def delete_user_training(request, user_id):
    """ Delete user's training record """

    user_id = request.POST.get('user', None)
    user_cert_id = request.POST.get('user_cert_id', None)

    # If inputs are invalid, raise a 400 error
    uApi.check_input_fields(request, ['user', 'user_cert_id'])

    user = uApi.get_user(user_id)
    usercert = user.usercert_set.filter(id=user_cert_id)
    print("USER CERT IS", usercert)

    if usercert.exists():
        usercert_obj = usercert.first()

        if usercert_obj.cert_file:
            file_path = usercert_obj.cert_file.path
            os.remove(file_path)

        dirpath = os.path.join(settings.MEDIA_ROOT, 'users', str(user_id), 'certificates', str(usercert_obj.cert.id))
        uApi.conditionally_add_missing_cert_for_user(user, usercert_obj)
        is_deleted = usercert.delete()

        if os.path.exists(dirpath) and os.path.isdir(dirpath):
            try:
                os.rmdir(dirpath)
            except OSError:
                # Directory not empty, do not delete
                pass

        if is_deleted:
            messages.success(request, 'Success! {0} deleted.'.format(usercert_obj.cert.name))
            return HttpResponseRedirect( reverse('app:user_trainings', args=[user_id]) )
        else:
            messages.error(request, 'Error! Failed to delete a {0} training record of {1}.'.format(usercert_obj.cert.name, usercert_obj.user.get_full_name()))
        messages.error(request, 'Error! Form is invalid.')

    return HttpResponseRedirect(reverse('app:user_trainings', args=[user_id]))



@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_loggedin_user_pi_admin
@require_http_methods(['GET'])
def download_user_cert(request, user_id, cert_id, filename):
    path = 'users/{0}/certificates/{1}/{2}'.format(user_id, cert_id, filename)
    return serve(request, path, document_root=settings.MEDIA_ROOT)
