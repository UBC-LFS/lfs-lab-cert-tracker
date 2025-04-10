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

        if not status and next:
            messages.error(request, 'Error: A status must be selected.')
            return HttpResponseRedirect(next)
        
        if not form_id or not room_id or not manager_id or not next:
            raise SuspiciousOperation
        
        RequestFormStatus.objects.create(
            form_id = form_id,
            room_id = room_id,
            manager_id = manager_id,
            operator_id = request.user.id,
            status = status
        )

        if status == REV_REQUEST_STATUS_DICT['Approved']:
            form = RequestForm.objects.get(id=form_id)
            room = Room.objects.get(id=room_id)

            check = [0] * room.managers.count()
            for i, manager in enumerate(room.managers.all()):
                status_filtered = RequestFormStatus.objects.filter(form_id=form_id, room_id=room_id, manager_id=manager.id)
                if status_filtered.exists():
                    for item in status_filtered:
                        if item.status == REV_REQUEST_STATUS_DICT['Approved']:
                            check[i] = 1
                            break
            
            count = 0
            for c in check:
                count += c
            print('count:', check, count, form.rooms.count())

            if count >= form.rooms.count():
                send_email(form, room)
                
        
        messages.success(request, 'Success! The status of {0} has been updated.'.format(func.display_room(room)))
        return HttpResponseRedirect(next)


def send_email(form, room):

    # Applicant
    subject, message = get_message(form, form.user, 'user')
    send(form.user, subject, message)

    # PI
    room_info = '<ul><li>{0}</li></ul>'.format(func.display_room(room))
    for manager in room.managers.all():
        subject, message = get_message(form, manager, 'pi', room_info)
        send(manager, subject, message)

    # Admin
    admins = User.objects.filter(is_superuser=True)
    if admins.count() > 0:
        room_info = '<ul>'
        for item in RequestFormStatus.objects.filter(form_id=form.id, room_id=room.id):
            if item.status == REV_REQUEST_STATUS_DICT['Approved']:
                room_info += '<li>{0} approved by {1}, {2}</li>'.format(func.display_room(item.room), func.display_user_full_name(item.operator), func.convert_date_to_str(item.created_at))
        room_info += '</ul>'
                
        for admin in admins:
            subject, message = get_message(form, admin, 'admin', room_info)
            send(admin, subject, message)


def get_message(form, admin, option, room_info=None):
    subject = ''
    message = ''

    if option == 'user':
        subject = 'Your key request has been approved by UBC LFS'
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>We are delighted to inform you that your key request has been approved today. Please visit <a href={1}>{1}</a> to check the status of your key request. Thank you.</div>
            {2}
        </div>
        '''.format(form.user.get_full_name(), settings.SITE_URL, EMAIL_FOOTER)
    
    elif option == 'pi':
        subject = "Notification: {0}'s Key Request Approval at UBC LFS".format(func.display_user_full_name(form.user))
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>This email is just a notification to inform you that {1}'s key request has been approved. Below are the details of the room.</div>
            {2}
            <div>Please visit <a href={3}>{3}</a> to check the latest status of key requests. Thank you.</div>
            {4}
        </div>
        '''.format(func.display_user_first_name(admin), func.display_user_first_name(form.user), room_info, settings.SITE_URL, EMAIL_FOOTER)

    elif option == 'admin':
        subject = "Notification: {0}'s Key Request Approval at UBC LFS".format(func.display_user_full_name(form.user))
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>This email is just a notification to inform you that {1}'s key request has been approved. Below are the details of the room.</div>
            {2}
            <div>Please visit <a href={3}>{3}</a> to check the latest status of key requests. Thank you.</div>
            {4}
        </div>
        '''.format(func.display_user_first_name(admin), func.display_user_first_name(form.user), room_info, settings.SITE_URL, EMAIL_FOOTER)
    return subject, message


def send(user, subject, message):
    sender = settings.EMAIL_FROM
    receiver = '{0} <{1}>'.format(func.display_user_full_name(user), user.email)

    print(f'An email notification is sent to {receiver}')

    msg = MIMEText(message, 'html')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver

    try:
        server = smtplib.SMTP(settings.EMAIL_HOST)
        server.sendmail(sender, receiver, msg.as_string())
    except Exception as e:
        print(e)
    finally:
        server.quit()


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