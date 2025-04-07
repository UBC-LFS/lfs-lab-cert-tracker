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
from django.db.models import Q, F, Max
from datetime import date
from django.forms.models import model_to_dict

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
from django.shortcuts import get_object_or_404
import smtplib
from email.mime.text import MIMEText
from django.apps import apps

from app import functions as appFunc
from . import functions as func
from .utils import *

from app.accesses import *
from .models import *
from .forms import *
from app.utils import *

from .mixins import RoomActionsMixin


@method_decorator([never_cache], name='dispatch')
class ManagerDashboard(LoginRequiredMixin, View):

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        query = {
            'building': request.GET.get('building'),
            'floor': request.GET.get('floor'),
            'number': request.GET.get('number'),
            'name': request.GET.get('name'),
            'status': request.GET.get('status')
        }

        total_forms, num_new_forms, form_list = func.get_manager_dashboard(request.user, query)
        num_filtered_forms = len(form_list)

        page = request.GET.get('page', 1)
        paginator = Paginator(form_list, NUM_PER_PAGE)

        try:
            forms = paginator.page(page)
        except PageNotAnInteger:
            forms = paginator.page(1)
        except EmptyPage:
            forms = paginator.page(paginator.num_pages)

        for form in forms:
            user_trainings, total_missing, total_expired = func.check_user_trainings(form.user, [room.id for room in form.rooms.all()])
            form.user_trainings = user_trainings
            form.total_missing = total_missing
            form.total_expired = total_expired
        
        return render(request, 'key_request/manager_dashboard/manager_dashboard.html', {
            'total_forms': total_forms,
            'num_new_forms': num_new_forms,
            'num_filtered_forms': num_filtered_forms,
            'forms': forms,
            'post_url': reverse('key_request:manager_dashboard'),
            'req_status_dict': REQUEST_STATUS_DICT,
            'search_filter_options': func.search_filter_options,
            'is_admin': True if request.user.is_superuser else False
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        form_id = request.POST.get('form')
        room_id = request.POST.get('room')
        manager_id = request.POST.get('manager')
        status = request.POST.get('status')
        next = request.POST.get('next')

        if not form_id or not room_id or not manager_id or not status or not next:
            raise SuspiciousOperation

        created = RequestFormStatus.objects.create(
            form_id = form_id,
            room_id = room_id,
            manager_id = manager_id,
            operator_id = request.user.id,
            status = status
        )
        
        print('here', created)

        messages.success(request, 'Success! Room {0} status has been updated.'.format(room_id))
        return HttpResponseRedirect(next)


@method_decorator([never_cache], name='dispatch')
class ManagerRooms(LoginRequiredMixin, View):

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        room_list = Room.objects.filter(managers__in=[request.user.id])
        total = len(room_list)

        query = {
            'building': request.GET.get('building'),
            'floor': request.GET.get('floor'),
            'number': request.GET.get('number'),
            'name': request.GET.get('name')
        }
        if query['building']:
            room_list = room_list.filter(building__code__icontains=query['building'])
        if query['floor']:
            room_list = room_list.filter(floor__name__icontains=query['floor'])
        if query['number']:
            room_list = room_list.filter(number__icontains=query['number'])

        num_filtered_rooms = len(room_list)

        page = request.GET.get('page', 1)
        paginator = Paginator(room_list, NUM_PER_PAGE)

        try:
            rooms = paginator.page(page)
        except PageNotAnInteger:
            rooms = paginator.page(1)
        except EmptyPage:
            rooms = paginator.page(paginator.num_pages)

        return render(request, 'key_request/manager_dashboard/manager_rooms.html', {
            'total_rooms': total,
            'num_filtered_rooms': num_filtered_rooms,
            'manager_rooms': rooms,
            'search_filter_options': func.search_filter_options
        })