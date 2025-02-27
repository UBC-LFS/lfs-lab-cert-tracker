import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from django.shortcuts import render, redirect
from django.views.static import serve
from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from django.db.models import Q, F
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.urls import reverse
from django.core.validators import validate_email
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.contrib.auth.models import User
from django.core.exceptions import SuspiciousOperation
from django.contrib.auth.mixins import LoginRequiredMixin


from io import BytesIO
# from cgi import escape # < python 3.8
from html import escape 
from xhtml2pdf import pisa
from datetime import datetime, date, timedelta

from .accesses import *
from .forms import *
from .functions import *
from .utils import *

from key_request import functions as kFunc

from lfs_lab_cert_tracker.models import *


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@require_http_methods(['GET'])
def index(request):
    full_name = get_data(request.META, 'full_name')
    last_name = get_data(request.META, 'last_name')
    email = get_data(request.META, 'email')
    username = get_data(request.META, 'username')

    if not request.user or not username:
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
    # return redirect('app:home')


# Users - classes


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['GET'])
def download_user_report_missing_trainings(request):

    # Find users who have missing certs
    result = 'ID,CWL,First Name,Last Name,Number of Missing Trainings,Missing Trainings\n'
    for user in get_users('active'):
        certs = ''
        missing_certs = get_user_missing_certs(user.id)
        if len(missing_certs) > 0:
            for i, cert in enumerate(missing_certs):
                certs += cert.name
                if i < len(missing_certs) - 1:
                    certs += '\n'

            result += '{0},{1},{2},{3},{4},"{5}"\n'.format(user.id, user.username, user.first_name, user.last_name, len(missing_certs), certs)

    return JsonResponse({ 'status': 'success', 'data': result })


@method_decorator([never_cache, access_loggedin_user_pi_admin], name='dispatch')
class UserDetails(LoginRequiredMixin, View):
    """ View user details """

    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)

        user_id = kwargs.get('user_id', None)
        if not user_id:
            raise SuspiciousOperation
        
        self.user = get_user_by_id(user_id)
        return setup

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        _, num_new_forms, _  = kFunc.get_manager_dashboard(request.user)

        return render(request, 'app/users/user_details.html', {
            'app_user': self.user,
            'user_labs': get_user_labs(self.user),
            'user_labs_pi': get_user_labs(self.user, is_pi=True),
            'user_certs': get_user_certs_with_info(self.user),
            'missing_certs': get_user_missing_certs(self.user.id),
            'expired_certs': get_user_expired_certs(self.user),
            'welcome_message': welcome_message(),
            'viewing': add_next_str_to_session(request, self.user),
            'num_new_forms': num_new_forms
        })


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_loggedin_user_pi_admin
@require_http_methods(['GET'])
def user_report(request, user_id):
    user = get_user_by_id(user_id)

    user_labs = get_user_labs(user)
    missing_certs = get_user_missing_certs(user.id)
    expired_certs = get_user_expired_certs(user)
    for user_lab in user_labs:
        required_certs = required_certs_in_lab(user_lab.lab.id)
        missing_certs_in_lab = required_certs.intersection(missing_certs)
        expired_certs_in_lab = required_certs.intersection(expired_certs)
        
        user_lab.required_certs = required_certs
        user_lab.missing_expired_certs = missing_certs_in_lab.union(expired_certs_in_lab)
    
    return render_to_pdf('app/users/user_report.html', {
        'app_user': user,
        'user_labs': user_labs,
        'user_certs': get_user_certs(user)
    })


@method_decorator([never_cache, access_loggedin_user_admin], name='dispatch')
class UserAreas(LoginRequiredMixin, View):
    """ Display user's areas """

    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)

        user_id = kwargs.get('user_id', None)
        if not user_id:
            raise SuspiciousOperation
        
        self.user = get_user_by_id(user_id)
        return setup

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        return render(request, 'app/users/user_areas.html', {
            'user_labs': get_user_labs(self.user),
            'user_labs_pi': get_user_labs(self.user, is_pi=True)
        })


@method_decorator([never_cache, access_loggedin_user_pi_admin], name='dispatch')
class MyTrainingRecord(LoginRequiredMixin, View):
    """ Display all training records of a user """

    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)

        user_id = kwargs.get('user_id', None)
        if not user_id:
            raise SuspiciousOperation
        
        self.user = get_user_by_id(user_id)
        return setup

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        viewing = {}
        if request.user.id != self.user.id and request.session.get('next'):
            viewing = get_viewing(request.session.get('next'))

        return render(request, 'app/users/my_training_record.html', {
            'app_user': self.user,
            'user_certs': get_user_certs_with_info(self.user),
            'missing_certs': get_user_missing_certs(self.user.id),
            'expired_certs': get_user_expired_certs(self.user),
            'viewing': viewing
        })


@method_decorator([never_cache, access_loggedin_user_pi_admin], name='dispatch')
class AddTrainingRecord(LoginRequiredMixin, View):
    """ Add training record of a user """

    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)

        user_id = kwargs.get('user_id', None)
        if not user_id:
            raise SuspiciousOperation
        
        self.user = get_user_by_id(user_id)
        return setup

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        viewing = {}
        if request.user.id != self.user.id and request.session.get('next'):
            viewing = get_viewing(request.session.get('next'))

        return render(request, 'app/users/add_training_record.html', {
            'app_user': self.user,
            'form': UserTrainingForm(initial={ 'user': self.user.id }),
            'viewing': viewing
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        form = UserTrainingForm(request.POST, request.FILES)

        if form.is_valid():
            data = form.cleaned_data

            completion_date = data['completion_date']
            expiry_year = completion_date.year + int(data['cert'].expiry_in_years)
            expiry_date = date(year=expiry_year, month=completion_date.month, day=completion_date.day)

            user_cert = UserCert.objects.create(
                user_id = self.user.id,
                cert_id = data['cert'].id,
                cert_file = request.FILES['cert_file'],
                uploaded_date = date.today(),
                completion_date = completion_date,
                expiry_date = expiry_date,
                by_api = False
            )
            
            if user_cert:
                messages.success(request, 'Success! {0} added.'.format(user_cert.cert.name))
            else:
                messages.error(request, "Error! Failed to add a training.")
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

        return HttpResponseRedirect(reverse('app:add_training_record', args=[self.user.id]))


@method_decorator([never_cache, access_loggedin_user_pi_admin], name='dispatch')
class UserTrainingDetailsView(LoginRequiredMixin, View):
    """ Display details of a training record of a user """

    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)

        user_id = kwargs.get('user_id', None)
        training_id = kwargs.get('training_id', None)

        if not user_id or not training_id:
            raise SuspiciousOperation

        user = get_user_by_id(user_id)
        self.user = user
        self.user_certs = user.usercert_set.filter(cert_id=training_id).order_by('-completion_date')
        self.training_id = training_id

        return setup

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        return render(request, 'app/trainings/user_training_details.html', {
            'app_user': self.user,
            'latest_user_cert': self.user_certs.first(),
            'user_certs': self.user_certs[1:],
            'viewing': add_next_str_to_session(request, self.user)
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        user_cert_id = request.POST.get('user_cert', None)

        if not user_cert_id:
            raise SuspiciousOperation

        user_cert = self.user.usercert_set.filter(id=user_cert_id)

        if user_cert.exists():
            user_cert_obj = user_cert.first()
            cert_name = user_cert_obj.cert.name

            user_cert_obj.delete()

            dirpath = os.path.join(settings.MEDIA_ROOT, 'users', str(self.user.id), 'certificates', str(self.training_id))
            if os.path.exists(dirpath) and os.path.isdir(dirpath) and len(os.listdir(dirpath)) == 0:
                try:
                    os.rmdir(dirpath)
                except OSError:
                    print('OSError: failed to remove a dir - ', dirpath)
            
            messages.success(request, 'Success! {0} deleted.'.format(cert_name))
            if self.user.usercert_set.filter(cert_id=self.training_id).count() > 0:
                return HttpResponseRedirect( request.POST.get('next') )
        else:
            messages.error(request, 'Error! Form is invalid.')

        return HttpResponseRedirect(reverse('app:my_training_record', args=[self.user.id]))


# Users - functions

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def delete_user(request):
    """ Delete a user """

    user = get_user_by_id(request.POST.get('user'))
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

    user = get_user_by_id(request.POST.get('user'))

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

    user = get_user_by_id(request.POST.get('user'))

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

    user = get_user_by_id(request.POST.get('user'))

    # delete all or not
    if len(request.POST.getlist('areas[]')) == 0:
        all_userlab = user.userlab_set.all()

        if len(all_userlab) > 0:
            if all_userlab.delete():
                return JsonResponse({ 'status': 'success', 'message': "Success! {0}'s all areas have deleted.".format(user.get_full_name()) })
            else:
                return JsonResponse({ 'status': 'error', 'message': 'Error! Failed to delete all areas.' })
        else:
            return JsonResponse({ 'status': 'warning', 'message': 'Warning! Nothing has changed.' })

    else:
        areas = request.POST.getlist('areas[]')
        all_userlab = user.userlab_set.all()

        report = update_or_create_areas_to_user(user, areas)
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



# Trainings - classes

# Trainings - functions

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def edit_training(request):
    """ Edit a training """

    training = get_cert_by_id( request.POST.get('training') )
    new_expiry_in_years = int(request.POST.get('expiry_in_years')) - training.expiry_in_years

    form = TrainingForm(request.POST, instance=training)
    if form.is_valid():
        updated_training = form.save()
        user_certs = UserCert.objects.filter(cert_id=training.id)

        objs = []
        if user_certs.count() > 0 and new_expiry_in_years != 0:
            for user_cert in user_certs:
                user_cert.expiry_date = date(user_cert.expiry_date.year + new_expiry_in_years, user_cert.expiry_date.month, user_cert.expiry_date.day)
                objs.append(user_cert)

            UserCert.objects.bulk_update(objs, ['expiry_date'])
            messages.success(request, 'Success! {0} training and {1} user training record(s) updated'.format(updated_training.name, len(objs)))
        else:
            messages.success(request, 'Success! {0} training updated'.format(updated_training.name))
    else:
        messages.error(request, 'An error occurred. Form is invalid. {0}'.format(get_error_messages(form.errors.get_json_data())))

    return redirect('app:all_trainings')


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def delete_training(request):
    """ Delete a training """

    training = get_cert_by_id(request.POST.get('training'))

    if training.delete():
        messages.success(request, 'Success! {0} deleted.'.format(training.name))
    else:
        messages.error(request, 'Error! Failed to delete {0}.'.format(training.name))

    return redirect('app:all_trainings')


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_loggedin_user_pi_admin
@require_http_methods(['GET'])
def download_user_cert(request, user_id, cert_id, filename):
    path = 'users/{0}/certificates/{1}/{2}'.format(user_id, cert_id, filename)
    return serve(request, path, document_root=settings.MEDIA_ROOT)



# Helper functions


def get_data(meta, field):
    data = settings.SHIB_ATTR_MAP[field]
    if data in meta:
        return meta[data]
    return None


def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    context = Context(context_dict)
    html  = template.render(context_dict)
    response = BytesIO()

    pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), response)
    if not pdf.err:
        return HttpResponse(response.getvalue(), content_type='application/pdf')
    return HttpResponse('Encountered errors <pre>%s</pre>' % escape(html))

