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
class AllRequests(LoginRequiredMixin, View):

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        query = {
            'building': request.GET.get('building'),
            'floor': request.GET.get('floor'),
            'number': request.GET.get('number'),
            'room': request.GET.get('room'),
            'name': request.GET.get('name'),
            'status': request.GET.get('status')
        }

        form_list, total_forms, new_forms = func.search_filters_for_requests(query)

        if query['status']:
            form_list = new_forms

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

        return render(request, 'key_request/admin/all_requests.html', {
            'total_forms': total_forms,
            'num_filtered_forms': num_filtered_forms,
            'forms': forms,
            'num_new_forms': new_forms.count(),
            'req_status_dict': REQUEST_STATUS_DICT,
            'search_filter_options': SEARCH_FILTER_OPTIONS,
            'is_admin': True if request.user.is_superuser else False
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        form_id = request.POST.get('form')
        operator = appFunc.get_user_name(request.user)
        status = request.POST.get('status')
        fs = RequestFormStatus.objects.create(form_id=form_id, operator=operator, status=status)
        if fs:
            messages.success(request, "Success! {0}'s status has been updated.".format(operator))
        else:
            messages.error(request, "Error! Failed to update {0}'s status for some reason. Please try again.".format(operator))
        return HttpResponseRedirect(request.POST.get('next'))


@method_decorator([never_cache], name='dispatch')
class AddTrainingToRoom(LoginRequiredMixin, RoomActionsMixin, View):

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        rooms = request.POST.getlist('rooms[]')
        training_id = request.POST.get('training')
        
        if not rooms:
            raise SuspiciousOperation

        if training_id:
            count = 0
            already_contained_rooms = []
            for room_id in rooms:
                room_filtered = Room.objects.filter(id=room_id)
                if room_filtered.exists():
                    room = room_filtered.first()
                    curr_training_ids = list(room.trainings.all().values_list('id', flat=True))
                    
                    if int(training_id) in curr_training_ids:
                        already_contained_rooms.append(f'ID: {room.id} - {room.building.code} {room.floor.name} - Room {room.number}')
                    else:
                        room.trainings.add(*[training_id])
                        count += 1

            if len(already_contained_rooms) > 0:
                room_numbers = '<ul>'
                for r in already_contained_rooms:
                    room_numbers += '<li>' + r + '</li>'
                room_numbers += '</ul>'
                training = Cert.objects.get(id=training_id)
                messages.warning(request, 'Warning! This required training ({0}) already exists in the following room(s). {1}'.format(training.name, room_numbers))

            if count > 0:
                messages.success(request, 'Success! The number of rooms ({0}) have been updated.'.format(count))
            else:
                messages.warning(request, 'Warning! There is no room to update.')
        else:
            messages.error(request, "Error! Please select the Required Training, and try again.")

        return HttpResponseRedirect(request.POST.get('next'))


@method_decorator([never_cache], name='dispatch')
class DeleteTrainingFromRoom(LoginRequiredMixin, RoomActionsMixin, View):

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        rooms = request.POST.getlist('rooms[]')
        training_id = request.POST.get('training')
        
        if not rooms:
            raise SuspiciousOperation

        if training_id:
            count = 0
            not_contained_rooms = []
            for room_id in rooms:
                room_filtered = Room.objects.filter(id=room_id)
                if room_filtered.exists():
                    room = room_filtered.first()
                    curr_training_ids = list(room.trainings.all().values_list('id', flat=True))
                    
                    if int(training_id) in curr_training_ids:
                        room.trainings.remove(*[training_id])
                        count += 1
                    else:
                        not_contained_rooms.append(f'ID: {room.id} - {room.building.code} {room.floor.name} - Room {room.number}')

            if len(not_contained_rooms) > 0:
                room_numbers = '<ul>'
                for r in not_contained_rooms:
                    room_numbers += '<li>' + r + '</li>'
                room_numbers += '</ul>'
                training = Cert.objects.get(id=training_id)
                messages.warning(request, 'Warning! This required training ({0}) does not exist in the following room(s). {1}'.format(training.name, room_numbers))

            if count > 0:
                messages.success(request, 'Success! The number of rooms ({0}) have been deleted.'.format(count))
            else:
                messages.warning(request, 'Warning! There is no room to delete.')
        else:
            messages.error(request, "Error! Please select the Required Training, and try again.")

        return HttpResponseRedirect(request.POST.get('next'))


# Helpers


def SEARCH_FILTER_OPTIONS():
    return {
        'buildings': Building.objects.values('code').distinct(),
        'floors': Floor.objects.values('name').distinct(),
        'rooms': Room.objects.values('number').distinct()
    }