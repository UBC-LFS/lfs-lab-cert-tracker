from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.views.decorators.cache import cache_control, never_cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.core.exceptions import SuspiciousOperation

from .accesses import *
from .forms import *
from .utils import *


@method_decorator([never_cache, access_pi_admin], name='dispatch')
class Index(LoginRequiredMixin, View):

    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)

        area_id = kwargs.get('area_id', None)
        if not area_id:
            raise SuspiciousOperation
        
        self.area = get_lab_by_id(area_id)

        self.tab = ''
        return setup

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        # if session has next value, delete it
        if request.session.get('next'):
            del request.session['next']

        required_certs = Cert.objects.filter(labcert__lab_id=self.area.id).order_by('name')

        users_in_area = []
                
        for userlab in self.area.userlab_set.all():
            user = userlab.user
            if is_pi_in_area(user.id, self.area.id): 
                user.is_pi = True
            else: 
                user.is_pi = False
            users_in_area.append(user)

        
        return render(request, 'app/area_details/index.html', {
            'area': self.area,
            'is_admin': request.user.is_superuser,
            'is_pi': is_pi_in_area(request.user.id, self.area.id),
            'required_certs': required_certs,
            'users_in_area': users_in_area
        })
    

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


@method_decorator([never_cache, access_pi_admin], name='dispatch')
class UsersMissingTrainings(LoginRequiredMixin, View):
    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)

        area_id = kwargs.get('area_id', None)
        if not area_id:
            raise SuspiciousOperation
        
        print('UsersMissingTrainings ======', area_id)
        self.area = get_lab_by_id(area_id)
        return setup
    
    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        required_certs = Cert.objects.filter(labcert__lab_id=self.area.id).order_by('name')

        users_missing_certs = []
        for user_lab in self.area.userlab_set.all():
            certs = Cert.objects.filter(usercert__user_id=user_lab.user.id).distinct()
            missing_certs = required_certs.difference(certs)
            if len(missing_certs) > 0:
                users_missing_certs.append({
                    'user': user_lab.user, 
                    'missing_certs': missing_certs.order_by('name')
                })
        
        return render(request, 'app/area_details/users_missing_trainings.html', {
            'area': self.area,
            'users_missing_certs': users_missing_certs
        })
    

@method_decorator([never_cache, access_pi_admin], name='dispatch')
class UsersExpiredTrainings(LoginRequiredMixin, View):
    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)

        area_id = kwargs.get('area_id', None)
        if not area_id:
            raise SuspiciousOperation
        
        self.area = get_lab_by_id(area_id)
        return setup
    
    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        required_certs = Cert.objects.filter(labcert__lab_id=self.area.id).order_by('name')

        users_expired_certs = []
        for user_lab in self.area.userlab_set.all():
            expired_certs = get_user_expired_certs(user_lab.user)
            expired_certs_in_lab = required_certs.intersection(expired_certs)

            if len(expired_certs_in_lab) > 0:
                users_expired_certs.append({
                    'user': user_lab.user, 
                    'expired_certs': expired_certs_in_lab.order_by('name')
                })

        return render(request, 'app/area_details/users_expired_trainings.html', {
            'area': self.area,
            'users_expired_certs': users_expired_certs
        })
    

@method_decorator([never_cache, access_pi_admin], name='dispatch')
class AddUserToArea(LoginRequiredMixin, View):
    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)

        area_id = kwargs.get('area_id', None)
        if not area_id:
            raise SuspiciousOperation
        
        self.area = get_lab_by_id(area_id)
        return setup
    
    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        return render(request, 'app/area_details/add_user_to_area.html', {
            'area': self.area,
            'is_admin': request.user.is_superuser,
            'is_pi': is_pi_in_area(request.user.id, self.area.id),
            'user_area_form': UserAreaForm(initial={ 'lab': self.area.id })
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
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



@method_decorator([never_cache, access_admin_only], name='dispatch')
class AddTrainingToArea(LoginRequiredMixin, View):
    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)

        area_id = kwargs.get('area_id', None)
        if not area_id:
            raise SuspiciousOperation
        
        self.area = get_lab_by_id(area_id)
        return setup
    
    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        
        # if session has next value, delete it
        if request.session.get('next'):
            del request.session['next']

        return render(request, 'app/area_details/add_training_to_area.html', {
            'area': self.area,
            'is_admin': request.user.is_superuser,
            'is_pi': is_pi_in_area(request.user.id, self.area.id),
            'area_training_form': AreaTrainingForm(initial={ 'lab': self.area.id })
        })
    

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
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