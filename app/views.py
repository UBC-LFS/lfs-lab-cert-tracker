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

# Settings


@method_decorator([never_cache, access_admin_only], name='dispatch')
class SettingIndex(LoginRequiredMixin, View):

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        return render(request, 'app/settings/setting_index.html', {
            'last_ten_users': User.objects.all().order_by('-date_joined')[:20]
        })

@method_decorator([never_cache, access_admin_only], name='dispatch')
class AllAreas(LoginRequiredMixin, View):

    form_class = AreaForm

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        area_list = Lab.objects.all()

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
            area.num_certs = area.labcert_set.count()
            area.num_users = area.userlab_set.count()

        return render(request, 'app/settings/all_areas.html', {
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
            messages.error(request, 'Error! Form is invalid. {0}'.format(get_error_messages(form.errors.get_json_data())))

        return redirect('app:all_areas')



@method_decorator([never_cache, access_admin_only], name='dispatch')
class AllTrainings(LoginRequiredMixin, View):
    """ Display all training records of a user """

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        training_list = Cert.objects.all()

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
        
        for cert in trainings:
            cert.num_users = cert.usercert_set.count()

        return render(request, 'app/settings/all_trainings.html', {
            'total_trainings': len(training_list),
            'trainings': trainings,
            'form': TrainingForm()
        })
    
    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        # Create a new training

        form = TrainingForm(request.POST)
        if form.is_valid():
            cert = form.save()
            if cert:
                messages.success(request, 'Success! {0} created.'.format(cert.name))
            else:
                messages.error(request, 'Error! Failed to create {0}. This training has already existed.'.format(cert.name))
        else:
            messages.error(request, 'Error! Form is invalid. {0}'.format(get_error_messages(form.errors.get_json_data())))

        return redirect('app:all_trainings')



@method_decorator([never_cache, access_admin_only], name='dispatch')
class AllUsers(LoginRequiredMixin, View):
    """ Display all users """

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        # if session has next value, delete it
        if request.session.get('next'):
            del request.session['next']

        user_list = get_users()

        # Pagination enables
        query = request.GET.get('q')
        if query:
            user_list = User.objects.filter(
                Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
            ).order_by('id').distinct()

        page = request.GET.get('page', 1)
        paginator = Paginator(user_list, NUM_PER_PAGE)

        try:
            users = paginator.page(page)
        except PageNotAnInteger:
            users = paginator.page(1)
        except EmptyPage:
            users = paginator.page(paginator.num_pages)

        for user in users:
            user.missing_certs = get_user_missing_certs(user.id)
            user.inactive = None
            user_inactive = UserInactive.objects.filter(user_id=user.id)
            if user_inactive.exists():
                user.inactive = user_inactive.first()

        areas = []
        for area in Lab.objects.all():
            area.has_lab_users = area.userlab_set.filter(role=UserLab.LAB_USER).values_list('user_id', flat=True)
            area.has_pis = area.userlab_set.filter(role=UserLab.PRINCIPAL_INVESTIGATOR).values_list('user_id', flat=True)
            areas.append(area)

        return render(request, 'app/settings/all_users.html', {
            'total_users': len(user_list),
            'users': users,
            'areas': areas,
            'roles': { 
                'LAB_USER': UserLab.LAB_USER, 
                'PI': UserLab.PRINCIPAL_INVESTIGATOR 
            }
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):

        # Edit a user
        user = get_user_by_id(request.POST.get('user'))
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            if form.save():
                messages.success(request, 'Success! {0} updated.'.format(user.get_full_name()))
            else:
                messages.error(request, 'Error! Failed to update {0}.'.format(user.get_full_name()))
        else:
            messages.error(request, 'Error! Form is invalid. {0}'.format(get_error_messages(form.errors.get_json_data())))

        return HttpResponseRedirect( request.POST.get('next') )


@method_decorator([never_cache, access_admin_only], name='dispatch')
class CreateUser(LoginRequiredMixin, View):
    """ Create a new user """

    form_class = UserForm

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        return render(request, 'app/settings/create_user.html', {
            'user_form': self.form_class(),
            'last_ten_users': User.objects.all().order_by('-date_joined')[:20]
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
                        sent = send_info_email(user)
                        if sent:
                            messages.success(request, 'Success! {0} created and sent an email.'.format(user.get_full_name()))
                        else:
                            messages.warning(request, 'Warning! {0} created, but failed to send an email due to {1}'.format(user.get_full_name(), sent.error))
                else:
                    messages.success(request, 'Success! {0} created.'.format(user.get_full_name()))
            else:
                messages.error(request, 'Error! Failed to create {0}. Please check your CWL.'.format(user.get_full_name()))
        else:
            messages.error(request, 'Error! Form is invalid. {0}'.format(get_error_messages(form.errors.get_json_data())))

        return redirect('app:create_user')



@method_decorator([never_cache, access_admin_only], name='dispatch')
class UserReportMissingTrainings(LoginRequiredMixin, View):
    """ Display an user report for missing trainings """

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        # Find users who have missing certs
        user_list = []
        for user in get_users('active'):
            missing_certs = get_user_missing_certs(user.id)
            if len(missing_certs) > 0: 
                user.missing_certs = missing_certs
                user_list.append(user)

        page = request.GET.get('page', 1)
        paginator = Paginator(user_list, 10)

        try:
            users = paginator.page(page)
        except PageNotAnInteger:
            users = paginator.page(1)
        except EmptyPage:
            users = paginator.page(paginator.num_pages)

        return render(request, 'app/settings/user_report_missing_trainings.html', {
            'total_users': len(user_list),
            'users': users,
            'download_user_report_missing_trainings_url': reverse('app:download_user_report_missing_trainings')
        })


@method_decorator([never_cache, access_admin_only], name='dispatch')
class APIUpdates(LoginRequiredMixin, View):
    """ Displays all the API updates made """
    
    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        
        # if session has next value, delete it
        if request.session.get('next'):
            del request.session['next']

        today = date.today()

        user_cert_list = UserCert.objects.filter(by_api=True).order_by('uploaded_date', 'user__last_name', 'user__first_name')

        stats = []
        for i in range(6, 0, -1):
            d = today - timedelta(i)
            stats.append({
                'date': convert_date_to_str(d),
                'count': user_cert_list.filter(uploaded_date=d).count()
            })
        
        date_from_q = request.GET.get('date_from')
        date_to_q = request.GET.get('date_to')        
        username_name_q = request.GET.get('q')
        training_q = request.GET.get('training')

        if bool(date_from_q) and bool(date_to_q):
            user_cert_list = user_cert_list.filter( Q(uploaded_date__gte=date_from_q) & Q(uploaded_date__lte=date_to_q) )
            today = '{0} ~ {1}'.format(date_from_q, date_to_q)
        elif bool(date_from_q):
            user_cert_list = user_cert_list.filter(uploaded_date=date_from_q)
            today = date_from_q
        elif bool(date_to_q):
            user_cert_list = user_cert_list.filter(uploaded_date=date_to_q)
            today = date_to_q
        else:
            user_cert_list = user_cert_list.filter(uploaded_date=today)
            today = convert_date_to_str(today)
        
        if bool(username_name_q):
            user_cert_list = user_cert_list.filter(
                Q(user__username__icontains=username_name_q) | Q(user__first_name__icontains=username_name_q) | Q(user__last_name__icontains=username_name_q)
            )
        if bool(training_q):
            user_cert_list = user_cert_list.filter(cert__name__icontains=training_q)

        page = request.GET.get('page', 1)
        paginator = Paginator(user_cert_list, NUM_PER_PAGE)

        try:
            user_certs = paginator.page(page)
        except PageNotAnInteger:
            user_certs = paginator.page(1)
        except EmptyPage:
            user_certs = paginator.page(paginator.num_pages)

        return render(request, 'app/settings/api_updates.html', {
            "total_user_certs": len(user_cert_list),
            "user_certs": user_certs,
            "today": today,
            "stats": stats
        })




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
class UserAreasView(LoginRequiredMixin, View):
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

        return render(request, 'app/areas/user_areas.html', {
            'user_labs': get_user_labs(self.user),
            'user_labs_pi': get_user_labs(self.user, is_pi=True)
        })


@method_decorator([never_cache, access_loggedin_user_pi_admin], name='dispatch')
class UserTrainingsView(LoginRequiredMixin, View):
    """ Display all training records of a user """

    form_class = UserTrainingForm

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

        return render(request, 'app/trainings/user_trainings.html', {
            'app_user': self.user,
            'user_certs': get_user_certs_with_info(self.user),
            'missing_certs': get_user_missing_certs(self.user.id),
            'expired_certs': get_user_expired_certs(self.user),
            'form': self.form_class(initial={ 'user': self.user.id }),
            'viewing': viewing
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        # Add a training record

        form = self.form_class(request.POST, request.FILES)

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

        return HttpResponseRedirect(reverse('app:user_trainings', args=[self.user.id]))


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

        return HttpResponseRedirect(reverse('app:user_trainings', args=[self.user.id]))


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


@method_decorator([never_cache, access_pi_admin], name='dispatch')
class AreaDetailsView(LoginRequiredMixin, View):
    """ Display all areas """

    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)

        area_id = kwargs.get('area_id', None)
        if not area_id:
            raise SuspiciousOperation
        
        self.area = get_lab_by_id(area_id)

        tab = request.GET.get('t', None)
        if not tab:
            raise Http404
        
        self.tab = tab
        return setup

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        # if session has next value, delete it
        if request.session.get('next'):
            del request.session['next']

        required_certs = Cert.objects.filter(labcert__lab_id=self.area.id).order_by('name')

        users_in_area = []
        users_missing_certs = []
        users_expired_certs = []

        if self.tab == 'users_in_area':
            for userlab in self.area.userlab_set.all():
                user = userlab.user
                if is_pi_in_area(user.id, self.area.id): 
                    user.is_pi = True
                else: 
                    user.is_pi = False
                
                users_in_area.append(user)

        elif self.tab == 'users_missing_records':
            for user_lab in self.area.userlab_set.all():
                certs = Cert.objects.filter(usercert__user_id=user_lab.user.id).distinct()
                missing_certs = required_certs.difference(certs)
                if len(missing_certs) > 0:
                    users_missing_certs.append({
                        'user': user_lab.user, 
                        'missing_certs': missing_certs.order_by('name')
                    })

        elif self.tab == 'users_expired_records':
            for user_lab in self.area.userlab_set.all():
                expired_certs = get_user_expired_certs(user_lab.user)
                expired_certs_in_lab = required_certs.intersection(expired_certs)

                if len(expired_certs_in_lab) > 0:
                    users_expired_certs.append({
                        'user': user_lab.user, 
                        'expired_certs': expired_certs_in_lab.order_by('name')
                    })
        
        return render(request, 'app/areas/area_details.html', {
            'area': self.area,
            'is_admin': request.user.is_superuser,
            'is_pi': is_pi_in_area(request.user.id, self.area.id),
            'required_certs': required_certs,
            'user_area_form': UserAreaForm(initial={ 'lab': self.area.id }),
            'area_training_form': AreaTrainingForm(initial={ 'lab': self.area.id }),
            'users_in_area': users_in_area,
            'users_missing_certs': users_missing_certs,
            'users_expired_certs': users_expired_certs,
            'current_tab': self.tab
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        """ Add a user to an area """

        username = request.POST.get('user', None)
        role = request.POST.get('role', None)
        area_id = request.POST.get('lab', None)

        if not area_id:
            messages.error(request, 'Error! Something went wrong. Area is required.')
            return HttpResponseRedirect(request.POST.get('next'))

        if not role:
            messages.error(request, 'Error! Something went wrong. Role is required.')
            return HttpResponseRedirect(request.POST.get('next'))

        user = get_user_by_username(username)

        # Check whether a user exists or not
        if user:
            user_lab = UserLab.objects.filter( Q(user_id=user.id) & Q(lab_id=area_id) )
            if not user_lab.exists():
                UserLab.objects.create(user_id=user.id, lab_id=area_id, role=role)
                valid_email = False
                valid_email_error = None

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
                messages.error(request, 'Error! Failed to add {0}. CWL already exists in this Area.'.format(user.username))
        else:
            messages.error(request, 'Error! Failed to add {0}. CWL does not exist in TRMS. Please go to a Users page then create the user by inputting the details before adding the user in the Area.'.format(username))

        return HttpResponseRedirect(request.POST.get('next'))


# Areas - functions

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def add_training_area(request):
    """ Add a training to an area """

    area_id = request.POST.get('lab', None)
    training_id = request.POST.get('cert', None)

    if not area_id:
        messages.error(request, 'Error! Something went wrong. Area is required.')
        return HttpResponseRedirect(request.POST.get('next'))

    if not training_id:
        messages.error(request, 'Error! Something went wrong. Training is required.')
        return HttpResponseRedirect(request.POST.get('next'))

    lab_cert = LabCert.objects.filter( Q(lab_id=area_id) & Q(cert_id=training_id) )

    if lab_cert.exists():
        lab_cert_obj = lab_cert.first()
        messages.error(request, 'Error! Failed to add Training. This training has already existed in this Area.'.format(lab_cert_obj.cert.name))
    else:
        form = AreaTrainingForm(request.POST)
        if form.is_valid():
            new_lab_cert = form.save()
            messages.success(request, 'Success! {0} added.'.format(new_lab_cert.cert.name))
        else:
            messages.error(request, 'Error! Form is invalid. {0}'.format(get_error_messages(form.errors.get_json_data())))

    return HttpResponseRedirect(request.POST.get('next'))


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def delete_training_in_area(request):
    """ Delete a required training in the area """

    area_id = request.POST.get('area', None)
    training_id = request.POST.get('training', None)

    if not area_id:
        messages.error(request, 'Error! Something went wrong. Area is required.')
        return HttpResponseRedirect(request.POST.get('next'))

    if not training_id:
        messages.error(request, 'Error! Something went wrong. Training is required.')
        return HttpResponseRedirect(request.POST.get('next'))

    lab_cert = LabCert.objects.filter( Q(lab_id=area_id) & Q(cert_id=training_id) )
    if lab_cert.exists():
        lab_cert_obj = lab_cert.first()
        if lab_cert_obj.delete():
            messages.success(request, 'Success! {0} deleted.'.format(lab_cert_obj.cert.name))
        else:
            messages.error(request, 'Error! Failed to delete {0}.'.format(lab_cert_obj.cert.name))
    else:
        training = get_cert_by_id(training_id)
        messages.error(request, 'Error! {0} does not exist in this Area.'.format(training.name))

    return HttpResponseRedirect(request.POST.get('next'))


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def edit_area(request):
    """ Update the name of area """

    area = get_lab_by_id(request.POST.get('area'))
    form = AreaForm(request.POST, instance=area)
    if form.is_valid():
        updated_area = form.save()
        if updated_area:
            messages.success(request, 'Success! {0} updated.'.format(updated_area.name))
        else:
            messages.error(request, 'Error! Failed to update {0}.'.format(area.name))
    else:
        messages.error(request, 'Error! Form is invalid. {0}'.format(get_error_messages(form.errors.get_json_data())))

    return redirect('app:all_areas')


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def delete_area(request):
    """ Delete an area """

    area = get_lab_by_id(request.POST.get('area'))
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

    if not user_id:
        messages.error(request, 'Error! Something went wrong. User is required.')
        return HttpResponseRedirect(request.POST.get('next'))

    if not area_id:
        messages.error(request, 'Error! Something went wrong. Area is required.')
        return HttpResponseRedirect(request.POST.get('next'))

    user = get_user_by_id(user_id)
    user_lab = UserLab.objects.filter( Q(user_id=user_id) & Q(lab_id=area_id) )

    if user_lab.exists():
        user_lab_obj = user_lab.first()

        role = ''
        prev_role = user_lab_obj.role

        if user_lab_obj.role == UserLab.LAB_USER:
            user_lab_obj.role = UserLab.PRINCIPAL_INVESTIGATOR
            role = 'Supervisor'
        else:
            user_lab_obj.role = UserLab.LAB_USER
            role = 'User'

        user_lab_obj.save(update_fields=['role'])

        if user_lab_obj.role != prev_role:
            messages.success(request, 'Success! {0} is now a {1}.'.format(user.get_full_name(), role))
        else:
            messages.error(request, 'Error! Failed to switch a role of {0}.'.format(user.get_full_name()))
    else:
        messages.error(request, 'Error! A user or an area data does not exist.')
    
    return HttpResponseRedirect(request.POST.get('next'))


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_pi_admin
@require_http_methods(['POST'])
def delete_user_in_area(request, area_id):
    """ Delete a user in the area """

    user_id = request.POST.get('user', None)
    area_id = request.POST.get('area', None)

    if not user_id:
        messages.error(request, 'Error! Something went wrong. User is required.')
        return HttpResponseRedirect(request.POST.get('next'))

    if not area_id:
        messages.error(request, 'Error! Something went wrong. Area is required.')
        return HttpResponseRedirect(request.POST.get('next'))

    user = get_user_by_id(user_id)
    user_lab = UserLab.objects.filter( Q(user_id=user_id) & Q(lab_id=area_id) )
    if user_lab.exists():
        user_lab_obj = user_lab.first()
        if user_lab_obj.delete():
            messages.success(request, 'Success! {0} deleted.'.format(user.get_full_name()))
        else:
            messages.error(request, 'Error! Failed to delete {0}.'.format(user.get_full_name()))
    else:
        messages.error(request, 'Error! A user or an area data does not exist.')
        
    return HttpResponseRedirect(request.POST.get('next'))


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

