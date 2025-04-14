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
from . import functions as func
from .utils import *

from key_request import functions as kFunc

from lfs_lab_cert_tracker.models import *


@method_decorator([never_cache, access_loggedin_user_pi_admin], name='dispatch')
class MyAccount(LoginRequiredMixin, View):
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

        return render(request, 'app/users/my_account.html', {
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
class MyWorkArea(LoginRequiredMixin, View):
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

        return render(request, 'app/users/my_work_area.html', {
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
class TrainingDetailsView(LoginRequiredMixin, View):
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
        return render(request, 'app/users/training_details.html', {
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


# Helper functions

def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    context = Context(context_dict)
    html  = template.render(context_dict)
    response = BytesIO()

    pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), response)
    if not pdf.err:
        return HttpResponse(response.getvalue(), content_type='application/pdf')
    return HttpResponse('Encountered errors <pre>%s</pre>' % escape(html))