import os
from io import BytesIO
from cgi import escape
from xhtml2pdf import pisa

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from django.shortcuts import render, redirect
from django.views.static import serve
from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse
from django.db.models import Q
from django.contrib.auth import authenticate, login as DjangoLogin
from django.contrib.auth.models import User as AuthUser
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.urls import reverse
from django.core.validators import validate_email
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.urls import resolve
from urllib.parse import urlparse

from lfs_lab_cert_tracker import api
from lfs_lab_cert_tracker import auth_utils
from lfs_lab_cert_tracker.forms import *

from lfs_lab_cert_tracker.models import UserInactive, Lab, Cert, UserCert, LabCert, UserLab
from lfs_lab_cert_tracker.utils import Api, access_all, access_admin_only, access_pi_admin, access_loggedin_user_pi_admin, access_loggedin_user_admin

# Set 50 users in a page
NUM_PER_PAGE = 50

uApi = Api()


def login(request):
    return render(request, 'accounts/login.html')


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@require_http_methods(['GET'])
def index(request):
    return redirect('/users/%d' % (request.user.id))


# Users - classes

@method_decorator([never_cache, login_required, access_admin_only], name='dispatch')
class AllUsersView(View):
    ''' Display all users '''

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        # if session has next value, delete it
        if request.session.get('next'):
            del request.session['next']

        user_list = uApi.get_users()

        # Pagination enables
        query = request.GET.get('q')
        if query:
            user_list = AuthUser.objects.filter(
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

        users = uApi.add_inactive_users(users)
        users = api.add_missing_certs(users)

        areas = api.get_areas()

        return render(request, 'users/all_users.html', {
            'users': users,
            'total_users': len(user_list),
            'areas': api.add_users_to_areas(areas),
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
class UserReportMissingTrainingsView(View):
    ''' Display an user report for missing trainings '''

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        all_users = uApi.get_users()

        # Find users who have missing certs
        user_list = []
        for user in api.add_missing_certs(all_users):
            if user.missing_certs != None:
                user_list.append(user)

        #user_list = users_in_missing_training.copy()

        # Pagination enables
        query = request.GET.get('q')
        if query:
            user_list = AuthUser.objects.filter(
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

        return render(request, 'users/user_report_missing_trainings.html', {
            'users': users,
            'total_users': len(user_list)
        })



@method_decorator([never_cache, login_required, access_admin_only], name='dispatch')
class NewUserView(View):
    ''' Create a new user '''

    form_class = UserForm

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        return render(request, 'users/new_user.html', {
            'user_form': self.form_class()
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save()
            if user:
                messages.success(request, 'Success! {0} created.'.format(user.username))
            else:
                messages.error(request, 'Error! Failed to create {0}. Please check your CWL.'.format(user.username))
        else:
            errors = form.errors.get_json_data()
            messages.error(request, 'Error! Form is invalid. {0}'.format( uApi.get_error_messages(errors) ) )

        return redirect('new_user')


@method_decorator([never_cache, login_required, access_loggedin_user_pi_admin], name='dispatch')
class UserDetailsView(View):
    ''' View user details '''

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

        return render(request, 'users/user_details.html', {
            'app_user': uApi.get_user(kwargs['user_id']),
            'user_lab_list': api.get_user_labs(user_id),
            'pi_user_lab_list': api.get_user_labs(user_id, is_principal_investigator=True),
            'user_certs': api.get_user_certs_404(user_id),
            'missing_cert_list': api.get_missing_certs(user_id),
            'expired_cert_list': api.get_expired_certs(user_id),
            'viewing': viewing
        })


# Users - functions


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def delete_user(request):
    ''' Delete a user '''

    user = uApi.get_user(request.POST.get('user'))
    if user.delete():
        messages.success(request, 'Success! {0} deleted.'.format(user.get_full_name()))
    else:
        messages.error(request, 'Error! Failed to delete {0}.'.format(user.get_full_name()))

    return HttpResponseRedirect( request.POST.get('next') )


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def switch_admin(request):
    ''' Switch a user to Admin or not Admin '''

    user = uApi.get_user(request.POST.get('user'))

    user.is_superuser = not user.is_superuser
    user.save(update_fields=['is_superuser'])

    if user.is_superuser:
        messages.success(request, 'Success! Granted administrator privileges to {0}.'.format(user.get_full_name()))
    else:
        messages.success(request, 'Success! Revoked administrator privileges of {0}.'.format(user.get_full_name()))

    return HttpResponseRedirect( request.POST.get('next') )


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def switch_inactive(request):
    ''' Switch a user to Active or Inactive '''

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

    return HttpResponseRedirect( request.POST.get('next') )


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def assign_user_areas(request):
    ''' Assign user's areas '''

    user = uApi.get_user(request.POST.get('user'))

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
@access_admin_only
@require_http_methods(['GET'])
def download_user_report_missing_trainings(request):
    '''Download a user report for missing trainings '''

    users = uApi.get_users()

    # Find users who have missing certs
    users_in_missing_training = []
    for user in api.add_missing_certs(users):
        if user.missing_certs != None:
            users_in_missing_training.append(user)

    return render_to_pdf('users/download_user_report_missing_trainings.html', {
        'users': users_in_missing_training,
    })



# Areas - classes


@method_decorator([never_cache, login_required, access_admin_only], name='dispatch')
class AllAreasView(View):
    ''' Display all areas '''

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

        return render(request, 'areas/all_areas.html', {
            'areas': areas,
            'total_labs': len(area_list),
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
            messages.error(request, 'Error! Form is invalid. {0}.'.format(get_error_messages(errors)))

        return redirect('all_areas')


@method_decorator([never_cache, login_required, access_loggedin_user_admin], name='dispatch')
class UserAreasView(View):
    ''' Display user's areas '''

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        return render(request, 'areas/user_areas.html', {
            'user_lab_list': api.get_user_labs(request.user.id),
            'pi_user_lab_list': api.get_user_labs(request.user.id, is_principal_investigator=True)
        })


@method_decorator([never_cache, login_required, access_pi_admin], name='dispatch')
class AreaDetailsView(View):
    ''' Display all areas '''

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

        users_in_area = []
        for userlab in area.userlab_set.all():
            user = userlab.user
            if uApi.is_pi_in_area(user.id, area_id): user.is_pi = True
            else: user.is_pi = False
            users_in_area.append(user)

        is_pi = uApi.is_pi_in_area(request.user.id, area_id)

        return render(request, 'areas/area_details.html', {
            'area': area,
            'required_trainings': required_trainings,
            'users_in_area': users_in_area,
            'is_admin': request.user.is_superuser,
            'is_pi': is_pi,
            'users_missing_certs': api.get_users_missing_certs(area_id),
            'users_expired_certs': api.get_users_expired_certs(area_id),
            'user_area_form': UserAreaForm(initial={ 'lab': area.id }),
            'area_training_form': AreaTrainingForm(initial={ 'lab': area.id })
        })


    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        ''' Add a user to an area '''

        username = request.POST.get('user')
        role = request.POST.get('role')
        area_id = request.POST.get('lab')

        found_user = AuthUser.objects.filter(username=username)

        # Check whether a user exists or not
        if found_user.exists():
            user = found_user.first()
            found_userlab = UserLab.objects.filter( Q(user_id=user.id) & Q(lab_id=area_id) )

            if found_userlab.exists() != True:
                userlab = UserLab.objects.create(user_id=user.id, lab_id=area_id, role=role)
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
                    messages.warning(request, 'Warning! Added {0} successfully, but failed to send an email. ({1} is invalid)'.format(user.get_full_name(), user.email))
            else:
                messages.error(request, 'Error! Failed to add {0}. CWL already exists in this area.'.format(user.username))
        else:
            messages.error(request, 'Error! Failed to add {0}. CWL does not exist in TRMS. Please go to a Users page then create the user by inputting the details before adding the user in the area.'.format(username))

        return HttpResponseRedirect( reverse('area_details', args=[area_id]) )




# Areas - functions


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def add_training_area(request):
    ''' Add a training to an area '''

    area_id = request.POST.get('lab', None)
    training_id = request.POST.get('cert', None)

    if area_id == None:
        messages.error(request, 'Error! Something went wrong. Area is required.')
        return redirect('all_areas')

    if training_id == None:
        messages.error(request, 'Error! Something went wrong. Training is required.')
        return HttpResponseRedirect( reverse('area_details', args=[area_id]) )

    area = uApi.get_area(area_id)
    training = uApi.get_training(training_id)

    labcert = uApi.get_labcert(request.POST.get('lab'), request.POST.get('cert'))

    if labcert == None:
        form = AreaTrainingForm(request.POST, instance=labcert)
        if form.is_valid():
            new_labcert = form.save()
            messages.success(request, 'Success! {0} added.'.format(new_labcert.cert.name))
        else:
            errors = form.errors.get_json_data()
            messages.error(request, 'Error! Form is invalid. {0}'.format( uApi.get_error_messages(errors) ))
    else:
        messages.error(request, 'Error! Failed to add Training. This training has already existed.'.format(labcert.cert.name))

    return HttpResponseRedirect( reverse('area_details', args=[area_id]) )



@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def delete_training_in_area(request):
    ''' Delete a required training in the area '''

    area_id = request.POST.get('area', None)
    training_id = request.POST.get('training', None)

    if area_id == None:
        messages.error(request, 'Error! Something went wrong. Area is required.')
        return redirect('all_areas')

    if training_id == None:
        messages.error(request, 'Error! Something went wrong. Training is required.')
        return HttpResponseRedirect( reverse('area_details', args=[area_id]) )

    area = uApi.get_area(area_id)
    training = uApi.get_training(training_id)

    labcert = uApi.get_labcert(area_id, training_id)

    if labcert == None:
        messages.error(request, 'Error! {0} does not exist in this area.'.format(training.name))
    else:
        if labcert.delete():
            messages.success(request, 'Success! {0} deleted.'.format(labcert.cert.name))
        else:
            messages.error(request, 'Error! Failed to delete {0}.'.format(labcert.cert.name))

    return HttpResponseRedirect( reverse('area_details', args=[area_id]) )



@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def edit_area(request):
    ''' Update the name of area '''

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
        messages.error(request, 'Error! Form is invalid. {0}.'.format(get_error_messages(errors)))

    return redirect('all_areas')



@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def delete_area(request):
    ''' Delete an area '''

    area = uApi.get_area(request.POST.get('area'))
    if area.delete():
        messages.success(request, 'Success! {0} deleted.'.format(area.name))
    else:
        messages.error(request, 'Error! Failed to delete {0}.'.format(area.name))

    return redirect('all_areas')


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_pi_admin
@require_http_methods(['POST'])
def switch_user_role_in_area(request, area_id):
    ''' Switch a user's role in the area '''

    user_id = request.POST.get('user', None)
    area_id = request.POST.get('area', None)

    if user_id == None:
        messages.error(request, 'Error! Something went wrong. User is required.')
        return HttpResponseRedirect( reverse('area_details', args=[area_id]) )

    if area_id == None:
        messages.error(request, 'Error! Something went wrong. Area is required.')
        return redirect('all_areas')

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

    return HttpResponseRedirect( reverse('area_details', args=[area_id]) )


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_pi_admin
@require_http_methods(['POST'])
def delete_user_in_area(request, area_id):
    ''' Delete a user in the area '''

    user_id = request.POST.get('user', None)
    area_id = request.POST.get('area', None)

    if user_id == None:
        messages.error(request, 'Error! Something went wrong. User is required.')
        return HttpResponseRedirect( reverse('area_details', args=[area_id]) )

    if area_id == None:
        messages.error(request, 'Error! Something went wrong. Area is required.')
        return redirect('all_areas')

    user = uApi.get_user(user_id)
    area = uApi.get_area(area_id)

    userlab = uApi.get_userlab(user_id, area_id)

    if userlab == None:
        messages.error(request, 'Error! A user or an area data does not exist.')
    else:
        if userlab.delete():
            messages.success(request, 'Success! {0} deleted.'.format(user.get_full_name()))
        else:
            messages.error(request, 'Error! Failed to delete {0}.'.format(user.get_full_name()))


    return HttpResponseRedirect( reverse('area_details', args=[area_id]) )


# -------------------------

# Trainings - classes

@method_decorator([never_cache, login_required, access_admin_only], name='dispatch')
class AllTrainingsView(View):
    ''' Display all training records of a user '''

    form_class = TrainingForm

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        cert_list = api.get_certs()

        # Pagination enables
        query = request.GET.get('q')
        if query:
            cert_list = Cert.objects.filter( Q(name__icontains=query) ).distinct()

        page = request.GET.get('page', 1)
        paginator = Paginator(cert_list, NUM_PER_PAGE)

        try:
            certs = paginator.page(page)
        except PageNotAnInteger:
            certs = paginator.page(1)
        except EmptyPage:
            certs = paginator.page(paginator.num_pages)

        return render(request, 'trainings/all_trainings.html', {
            'certs': certs,
            'total_certs': len(cert_list),
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

        return redirect('all_trainings')



@method_decorator([never_cache, login_required, access_loggedin_user_pi_admin], name='dispatch')
class UserTrainingsView(View):
    ''' Display all training records of a user '''

    form_class = UserTrainingForm

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        user_id = kwargs['user_id']
        app_user = uApi.get_user(user_id)

        viewing = {}
        if request.user.id != user_id and request.session.get('next'):
            viewing = uApi.get_viewing(request.session.get('next'))

        return render(request, 'trainings/user_trainings.html', {
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

            completion_date = dt.datetime(year=year, month=month, day=day)

            # Calculate a expiry year
            expiry_year = year + int(cert['expiry_in_years'])
            expiry_date = dt.datetime(year=expiry_year, month=month, day=day)

            result = api.update_or_create_user_cert(data['user'], data['cert'], files['cert_file'], completion_date, expiry_date)

            # Whether user's certficiate is created successfully or not
            if result:
                messages.success(request, 'Success! {0} added.'.format(cert['name']))
                res = { 'user_id': user_id, 'cert_id': result['cert'] }
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

        return HttpResponseRedirect( reverse('user_trainings', args=[user_id]) )



@method_decorator([never_cache, login_required, access_loggedin_user_pi_admin], name='dispatch')
class UserTrainingDetailsView(View):
    ''' Display details of a training record of a user '''

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        user_id = kwargs['user_id']
        training_id = kwargs['training_id']

        viewing = {}
        if request.user.id != user_id and request.session.get('next'):
            viewing = uApi.get_viewing(request.session.get('next'))

        return render(request, 'trainings/user_training_details.html', {
            'app_user': uApi.get_user(user_id),
            'user_cert': api.get_user_cert_404(user_id, training_id),
            'viewing': viewing
        })


# Trainings - functions

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def edit_training(request):
    ''' Edit a cert '''

    training_id = request.POST.get('training')

    training = uApi.get_training(training_id)
    form = TrainingNameForm(request.POST, instance=training)
    if form.is_valid():
        updated_cert = form.save()
        messages.success(request, 'Success! {0} updated'.format(updated_cert.name))
    else:
        errors = form.errors.get_json_data()
        messages.error(request, 'An error occurred. Form is invalid. {0}'.format( uApi.get_error_messages(errors) ))

    return redirect('all_trainings')



@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def delete_training(request):
    ''' Delete a training '''

    training = uApi.get_training(request.POST.get('training'))

    if training.delete():
        messages.success(request, 'Success! {0} deleted.'.format(training.name))
    else:
        messages.error(request, 'Error! Failed to delete {0}.'.format(training.name))

    return redirect('all_trainings')

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_loggedin_user_admin
@require_http_methods(['POST'])
def delete_user_training(request, user_id):
    ''' Delete user's training record '''

    user_id = request.POST.get('user', None)
    training_id = request.POST.get('training', None)

    # If inputs are invalid, raise a 400 error
    uApi.check_input_fields(request, ['user', 'training'])


    user = uApi.get_user(user_id)
    usercert = user.usercert_set.filter(cert_id=training_id)

    if usercert.exists():
        usercert_obj = usercert.first()

        is_dir_deleted = False
        dirpath = os.path.join(settings.MEDIA_ROOT, 'users', str(user_id), 'certificates', str(training_id))

        is_deleted = usercert.delete()

        if os.path.exists(dirpath) and os.path.isdir(dirpath):
            os.rmdir(dirpath)
            is_dir_deleted = True

        if is_deleted and is_dir_deleted == True:
            messages.success( request, 'Success! {0} deleted.'.format(usercert_obj.cert.name) )
            return HttpResponseRedirect( reverse('user_trainings', args=[user_id]) )
        else:
            messages.error( request, 'Error! Failed to delete a {0} training record of {1}.'.format(usercert_obj.cert.name, usercert_obj.user.get_full_name()) )
    else:
        messages.error(request, 'Error! Form is invalid.')

    return HttpResponseRedirect( reverse('user_trainings', args=[user_id]) )



@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_loggedin_user_pi_admin
@require_http_methods(['GET'])
def download_user_cert(request, user_id, cert_id, filename):
    path = 'users/{0}/certificates/{1}/{2}'.format(user_id, cert_id, filename)
    return serve(request, path, document_root=settings.MEDIA_ROOT)



#------------------------




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

# Certificates




"""
@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@require_http_methods(['GET'])
def show_error(request, error_msg=''):
    return render(request, 'lfs_lab_cert_tracker/error.html', {
        'loggedin_user': request.user,
        'error_msg': error_msg
    })
"""

# Exception handlers

def bad_request(request, exception, template_name='400.html'):
    ''' Exception handlder for bad request '''
    return render(request, '400.html', context={}, status=400)

def permission_denied(request, exception, template_name="403.html"):
    ''' Exception handlder for permission denied '''

    return render(request, '403.html', context={}, status=403)

def page_not_found(request, exception, template_name="404.html"):
    ''' Exception handlder for page not found '''

    return render(request, '404.html', context={}, status=404)


# for local testing

def local_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(username=request.POST['username'], password=request.POST['password'])
            if user is not None:
                DjangoLogin(request, user)
                return redirect('index')

    return render(request, 'accounts/local_login.html', { 'form': LoginForm() })





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



"""
@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@auth_utils.admin_only
@require_http_methods(['GET', 'POST'])
def users(request):
    ''' Display all users '''

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
            messages.error(request, 'Error! Form is invalid. {0}'.format( uApi.get_error_messages(errors) ) )

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
"""

"""
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
            messages.error(request, 'Error! Form is invalid. {0}'.format( uApi.get_error_messages(errors) ))

    return HttpResponseRedirect( request.POST.get('next') )
"""
