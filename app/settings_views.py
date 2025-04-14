from django.conf import settings
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponseRedirect, JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.views.decorators.cache import cache_control, never_cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.db.models import Q
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from django.contrib.auth.models import User
from lfs_lab_cert_tracker.models import Lab, Cert, UserLab, UserCert, UserInactive
from .forms import AreaForm, TrainingForm, UserForm
from .accesses import access_admin_only

from . import functions as func
from .utils import NUM_PER_PAGE

from datetime import datetime


@method_decorator([never_cache, access_admin_only], name='dispatch')
class Index(LoginRequiredMixin, View):

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        return render(request, 'app/settings/index.html', {
            'recent_users': User.objects.all().order_by('-date_joined')[:20]
        })
    

# Area

@method_decorator([never_cache, access_admin_only], name='dispatch')
class AllAreas(LoginRequiredMixin, View):

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
            'total_areas': len(area_list)
        })


@method_decorator([never_cache, access_admin_only], name='dispatch')
class CreateArea(LoginRequiredMixin, View):
    """ Create a new area """

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        return render(request, 'app/settings/create_area.html', {
            'form': AreaForm(),
            'recent_areas': Lab.objects.all().order_by('-id')[:20]
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        form = AreaForm(request.POST)
        if form.is_valid():
            area = form.save()
            if area:
                messages.success(request, 'Success! {0} has been created.'.format(area.name))
            else:
                messages.error(request, 'Error! Failed to create {0}.'.format(area.name))
        else:
            messages.error(request, 'Error! Form is invalid. {0}'.format(func.get_error_messages(form.errors.get_json_data())))

        return redirect('app:create_area')




@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def edit_area(request):
    """ Update the name of area """

    area = func.get_lab_by_id(request.POST.get('area'))
    form = AreaForm(request.POST, instance=area)
    if form.is_valid():
        updated_area = form.save()
        if updated_area:
            messages.success(request, 'Success! {0} has been updated.'.format(updated_area.name))
        else:
            messages.error(request, 'Error! Failed to update {0}.'.format(area.name))
    else:
        messages.error(request, 'Error! Form is invalid. {0}'.format(func.get_error_messages(form.errors.get_json_data())))

    return redirect('app:all_areas')


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def delete_area(request):
    """ Delete an area """

    area = func.get_lab_by_id(request.POST.get('area'))
    if area.delete():
        messages.success(request, 'Success! {0} has been deleted.'.format(area.name))
    else:
        messages.error(request, 'Error! Failed to delete {0}.'.format(area.name))

    return redirect('app:all_areas')


# Training

@method_decorator([never_cache, access_admin_only], name='dispatch')
class AllTrainings(LoginRequiredMixin, View):
    """ Display all training records """

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
            'trainings': trainings
        })


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def edit_training(request):
    """ Edit a training """

    training = func.get_cert_by_id( request.POST.get('training') )
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
        messages.error(request, 'An error occurred. Form is invalid. {0}'.format(func.get_error_messages(form.errors.get_json_data())))

    return redirect('app:all_trainings')


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def delete_training(request):
    """ Delete a training """

    training = func.get_cert_by_id(request.POST.get('training'))

    if training.delete():
        messages.success(request, 'Success! {0} deleted.'.format(training.name))
    else:
        messages.error(request, 'Error! Failed to delete {0}.'.format(training.name))

    return redirect('app:all_trainings')



@method_decorator([never_cache, access_admin_only], name='dispatch')
class CreateTraining(LoginRequiredMixin, View):
    """ Create a new training """

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        return render(request, 'app/settings/create_training.html', {
            'form': TrainingForm(),
            'recent_trainings': Cert.objects.all().order_by('-id')[:20]
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        form = TrainingForm(request.POST)
        if form.is_valid():
            cert = form.save()
            if cert:
                messages.success(request, 'Success! {0} has been created.'.format(cert.name))
            else:
                messages.error(request, 'Error! Failed to create {0}. This training has already existed.'.format(cert.name))
        else:
            messages.error(request, 'Error! Form is invalid. {0}'.format(func.get_error_messages(form.errors.get_json_data())))

        return redirect('app:create_training')


# User


@method_decorator([never_cache, access_admin_only], name='dispatch')
class AllUsers(LoginRequiredMixin, View):
    """ Display all users """

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        # if session has next value, delete it
        if request.session.get('next'):
            del request.session['next']

        user_list = func.get_users()

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
            user.missing_certs = func.get_user_missing_certs(user.id)
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
        user = func.get_user_by_id(request.POST.get('user'))
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            if form.save():
                messages.success(request, 'Success! {0} has been updated.'.format(user.get_full_name()))
            else:
                messages.error(request, 'Error! Failed to update {0}.'.format(user.get_full_name()))
        else:
            messages.error(request, 'Error! Form is invalid. {0}'.format(func.get_error_messages(form.errors.get_json_data())))

        return HttpResponseRedirect( request.POST.get('next') )




@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def delete_user(request):
    """ Delete a user """

    user = func.get_user_by_id(request.POST.get('user'))
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

    user = func.get_user_by_id(request.POST.get('user'))

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

    user = func.get_user_by_id(request.POST.get('user'))

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

    user = func.get_user_by_id(request.POST.get('user'))

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

        report = func.update_or_create_areas_to_user(user, areas)
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



@method_decorator([never_cache, access_admin_only], name='dispatch')
class CreateUser(LoginRequiredMixin, View):
    """ Create a new user """

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        return render(request, 'app/settings/create_user.html', {
            'form': UserForm(),
            'recent_users': User.objects.all().order_by('-date_joined')[:20]
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        form = UserForm(request.POST)
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
                        sent = func.send_info_email(user)
                        if sent:
                            messages.success(request, 'Success! {0} has been created and sent an email.'.format(user.get_full_name()))
                        else:
                            messages.warning(request, 'Warning! {0} has been created, but failed to send an email due to {1}'.format(user.get_full_name(), sent.error))
                else:
                    messages.success(request, 'Success! {0} has been created.'.format(user.get_full_name()))
            else:
                messages.error(request, 'Error! Failed to create {0}. Please check your CWL.'.format(user.get_full_name()))
        else:
            messages.error(request, 'Error! Form is invalid. {0}'.format(func.get_error_messages(form.errors.get_json_data())))

        return redirect('app:create_user')



@method_decorator([never_cache, access_admin_only], name='dispatch')
class UserReportMissingTrainings(LoginRequiredMixin, View):
    """ Display an user report for missing trainings """

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        # Find users who have missing certs
        user_list = []
        for user in func.get_users('active'):
            missing_certs = func.get_user_missing_certs(user.id)
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



@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['GET'])
def download_user_report_missing_trainings(request):

    # Find users who have missing certs
    result = 'ID,CWL,First Name,Last Name,Number of Missing Trainings,Missing Trainings\n'
    for user in func.get_users('active'):
        certs = ''
        missing_certs = func.get_user_missing_certs(user.id)
        if len(missing_certs) > 0:
            for i, cert in enumerate(missing_certs):
                certs += cert.name
                if i < len(missing_certs) - 1:
                    certs += '\n'

            result += '{0},{1},{2},{3},{4},"{5}"\n'.format(user.id, user.username, user.first_name, user.last_name, len(missing_certs), certs)

    return JsonResponse({ 'status': 'success', 'data': result })




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
                'date': func.convert_date_to_str(d),
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
            today = func.convert_date_to_str(today)
        
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


