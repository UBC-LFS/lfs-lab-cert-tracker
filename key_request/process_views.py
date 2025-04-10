from django.conf import settings
from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect
from django.http import JsonResponse, Http404
from django.contrib import messages
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
import smtplib
from email.mime.text import MIMEText

from app.accesses import *
from app import functions as appFunc
from app.utils import *

from .models import *
from .forms import *
from . import functions as func
from .utils import *


@method_decorator([never_cache], name='dispatch')
class SelectRooms(LoginRequiredMixin, View):

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        rooms = Room.objects.all()

        print(func.preprocess_rooms(rooms))
        return render(request, 'key_request/process/select_rooms.html', {
            'buildings': Building.objects.all(),
            'floors': Floor.objects.all(),
            'rooms': func.preprocess_rooms(rooms),
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        request.session['selected_rooms'] = request.POST.getlist('rooms[]')

        return JsonResponse({'status': 'success', 'next': request.POST['next']})


@method_decorator([never_cache], name='dispatch')
class CheckUserTrainings(LoginRequiredMixin, View):

    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)

        selected_rooms = request.session.get('selected_rooms')
        if not selected_rooms:
            raise Http404

        self.selected_rooms = selected_rooms
        return setup

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        rooms = []
        for room_id in self.selected_rooms:
            room = Room.objects.get(id=room_id)
            rooms.append(room)

        user_trainings, total_missing, total_expired = func.check_user_trainings(request.user, self.selected_rooms)

        return render(request, 'key_request/process/check_user_trainings.html', {
            'rooms': rooms,
            'user_trainings': user_trainings,
            'total_missing': total_missing,
            'total_expired': total_expired
        })


@method_decorator([never_cache], name='dispatch')
class SubmitForm(LoginRequiredMixin, View):
    form_class = KeyRequestForm

    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)

        selected_rooms = request.session.get('selected_rooms')
        _, total_missing, total_expired = func.check_user_trainings(request.user, selected_rooms)
        if not selected_rooms or total_missing != 0 or total_expired != 0:
            raise Http404

        self.selected_rooms = selected_rooms
        return setup

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        room_info = []
        for rid in self.selected_rooms:
            room = Room.objects.get(id=rid)
            room_info.append({
                'id': room.id,
                'building': room.building.code,
                'floor': room.floor.name,
                'number': room.number
            })

        return render(request, 'key_request/process/submit_form.html', {
            'form': self.form_class(initial={'user': request.user.id }),
            'basic_info': [
                ('Applicant First Name', request.user.first_name),
                ('Applicant Last Name', request.user.last_name),
                ('UBC CWL User Name', request.user.username),
                ('Applicant UBC Email', request.user.email)
            ],
            'room_info': room_info
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        if not request.POST.get('agree'):
            messages.error(request, 'Error! Please read the <strong>Requirement to Proceed</strong>, and try again.')
            return redirect('key_request:submit_form')

        form = self.form_class(request.POST)
        rooms = request.POST.getlist('rooms[]')
        operator = appFunc.get_user_name(request.user)

        if form.is_valid() and len(rooms) > 0:
            req_form = form.save()
            if req_form:

                # Add selected rooms to this key request
                req_form.rooms.add( *rooms )

                # Send a confirmation email
                send_email(req_form)

                # Delete the selected rooms in the session
                del request.session['selected_rooms']

                messages.success(request, "Success! {0}'s key request form has been submitted.".format(operator))
                return redirect('key_request:index')
            else:
                messages.error(request, "Error! Failed to submit {0}'s key request form for some reason. Please try again.".format(operator))
        else:
            messages.error(request, 'Error! Form is invalid. {0}'.format(get_error_messages(form.errors.get_json_data())))

        return redirect('key_request:submit_form')


def send_email(form):
    submitted_at = form.submitted_at.strftime('%Y-%m-%d')
    user_rooms = ''
    pi_rooms = {}
    for room in form.rooms.all():
        room_info = '<li>{0}</li>'.format(func.display_room(room))
        user_rooms += room_info

        for manager in room.managers.all():
            if manager.id not in pi_rooms.keys():
                pi_rooms[manager.id] = []

            pi_rooms[manager.id].append({
                'pi': manager,
                'room': room_info,
                'applicant': form.user,
                'submitted_at': submitted_at
            })

    if len(user_rooms) > 0:
        subject, message = get_message(form.user, user_rooms, 'user', submitted_at)
        send(form.user, subject, message)

    if len(pi_rooms.keys()) > 0:
        for key, value in pi_rooms.items():
            if len(value) > 0:
                rooms = ''
                for item in value:
                    rooms += item['room']
                subject, message = get_message(value[0]['pi'], rooms, 'pi', value[0]['submitted_at'], value[0]['applicant'])
                send(value[0]['pi'], subject, message)

    admins = User.objects.filter(is_superuser=True)
    if admins.count() > 0:
        for admin in admins:
            subject, message = get_message(admin, user_rooms, 'admin', submitted_at, form.user)
            send(admin, subject, message)
            

def get_message(receiver, rooms, option, submitted_at, applicant=None):
    subject = ''
    message = ''

    if option == 'user':
        subject = 'Confirmation of Key Request at UBC LFS'
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>You have submitted the following key request on {1}.</div>
            <ul>{2}</ul>
            <div>Please visit <a href={3}>{3}</a> to check the status of your key request. Thank you.</div>
            <br />
            <div>
                <b>Please note that if you try to access the LFS Training Record Management System off campus,
                you must be connected via
                <a href="https://it.ubc.ca/services/email-voice-internet/myvpn">UBC VPN</a>.</b>
            </div>
            <br />
            <p>Best regards,</p>
            <p>LFS Training Record Management System</p>
        </div>
        '''.format(receiver.get_full_name(), submitted_at, rooms, settings.SITE_URL)

    elif option == 'pi':
        subject = 'Notification of Key Request at UBC LFS'
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>{1} submitted a key request form on {2}.</div>
            <ul>{3}</ul>
            <div>Please visit <a href={4}>{4}</a> to check the status of {1}'s key request form. Thank you.</div>
            <br />
            <div>
                <b>Please note that if you try to access the LFS Training Record Management System off campus,
                you must be connected via
                <a href="https://it.ubc.ca/services/email-voice-internet/myvpn">UBC VPN</a>.</b>
            </div>
            <br />
            <p>Best regards,</p>
            <p>LFS Training Record Management System</p>
        </div>
        '''.format(receiver.get_full_name(), applicant.get_full_name(), submitted_at, rooms, settings.SITE_URL)
    
    elif option == 'admin':
        subject = 'Notification of Key Request at UBC LFS'
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>{1} submitted a key request form on {2}.</div>
            <ul>{3}</ul>
            <div>Please visit <a href={4}>{4}</a> to check the status of {1}'s key request form. Thank you.</div>
            <br />
            <div>
                <b>Please note that if you try to access the LFS Training Record Management System off campus,
                you must be connected via
                <a href="https://it.ubc.ca/services/email-voice-internet/myvpn">UBC VPN</a>.</b>
            </div>
            <br />
            <p>Best regards,</p>
            <p>LFS Training Record Management System</p>
        </div>
        '''.format(receiver.get_full_name(), applicant.get_full_name(), submitted_at, rooms, settings.SITE_URL)

    return subject, message


def send(user, subject, message):
    sender = settings.EMAIL_FROM
    receiver = '{0} <{1}>'.format(user.get_full_name(), user.email)

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
