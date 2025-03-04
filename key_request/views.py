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

@method_decorator([never_cache], name='dispatch')
class Index(LoginRequiredMixin, View):

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        form_list = request.user.requestform_set.all()

        page = request.GET.get('page', 1)
        paginator = Paginator(form_list, NUM_PER_PAGE)

        try:
            forms = paginator.page(page)
        except PageNotAnInteger:
            forms = paginator.page(1)
        except EmptyPage:
            forms = paginator.page(paginator.num_pages)

        for form in forms:
            form.status = 'Pending by Supervisor'
            form.status_created_at = None

            room_ids = []
            num_managers = 0
            manager_approvals = 0
            for room in form.rooms.all():
                room_ids.append(room.id)
                num_managers += room.managers.count()

            for room in form.rooms.all():
                for manager in room.managers.all():
                    manager.status = None
                    status_filtered = form.requestformstatus_set.filter(form_id=form.id, room_id=room.id, manager_id=manager.id, status=APPROVED)
                    if status_filtered.exists():
                        manager_approvals += 1
                        if not form.status_created_at or status_filtered.first().created_at > form.status_created_at:
                            form.status_created_at = status_filtered.first().created_at

            if num_managers == manager_approvals:
                form.status = 'Approved'

            user_trainings, total_missing, total_expired = func.check_user_trainings(form.user, room_ids)
            form.user_trainings = user_trainings
            form.total_missing = total_missing
            form.total_expired = total_expired

        return render(request, 'key_request/index.html', {
            'total_forms': len(form_list),
            'forms': forms,
            'is_admin': True if request.user.is_superuser else False
        })


# Key Request Process

@method_decorator([never_cache], name='dispatch')
class SelectRooms(LoginRequiredMixin, View):

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        rooms = Room.objects.all()
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


def send_email(obj):
    user_rooms = ''
    pi_rooms = {}
    for room in obj.rooms.all():
        room_info = '<li>{0} {1} - Room {2}</li>'.format(room.building.code, room.floor.name, room.number)
        user_rooms += room_info

        for manager in room.managers.all():
            if manager.id not in pi_rooms.keys():
                pi_rooms[manager.id] = []

            pi_rooms[manager.id].append({
                'pi': manager,
                'room': room_info,
                'applicant': obj.user,
                'submitted_date': obj.submitted_at.strftime('%Y-%m-%d')
            })

    if len(user_rooms) > 0:
        subject, message = message_for_user(obj.user, user_rooms, 'user')
        send(obj.user, subject, message)

    if len(pi_rooms.keys()) > 0:
        for key, value in pi_rooms.items():
            if len(value) > 0:
                rooms = ''
                for item in value:
                    rooms += item['room']
                subject, message = message_for_user(value[0]['pi'], rooms, 'pi', value[0]['applicant'], value[0]['submitted_date'])
                send(value[0]['pi'], subject, message)


def message_for_user(receiver, rooms, option, applicant=None, submitted_date=None):
    subject = ''
    message = ''

    if option == 'user':
        subject = 'Confirmation of Key Request at UBC LFS'
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>We have received your key request as follows.</div>
            <ul>{1}</ul>
            <div>Please visit <a href={2}>{2}</a> to check the status of your key request. Thank you.</div>
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
        '''.format(receiver.get_full_name(), rooms, settings.SITE_URL)

    elif option == 'pi':
        subject = 'Notification of Key Request at UBC LFS'
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>{1} has submitted a key request form on {2}.</div>
            <ul>{3}</ul>
            <div>Please visit <a href={4}>{4}</a> to update the status of {1}'s key request form. Thank you.</div>
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
        '''.format(receiver.get_full_name(), applicant.get_full_name(), submitted_date, rooms, settings.SITE_URL)
    return subject, message


def send(receiver, subject, message):
    sender = settings.EMAIL_FROM
    receiver = '{0} <{1}>'.format(receiver.get_full_name(), receiver.email)

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


# For Admin


@method_decorator([never_cache], name='dispatch')
class ViewFormDetails(LoginRequiredMixin, View):

    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)

        form_id = kwargs.get('form_id')
        tab = request.GET.get('t')
        next = func.get_next(request)

        if not form_id or not tab or not next:
            raise SuspiciousOperation

        self.form = get_object_or_404(RequestForm, id=form_id)
        self.tab = tab
        self.url = reverse('key_request:view_form_details', args=[form_id])
        self.next = next

        return setup

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        user_trainings, total_missing, total_expired = func.check_user_trainings(self.form.user, [room.id for room in self.form.rooms.all()])
        self.form.user_trainings = user_trainings
        self.form.total_missing = total_missing
        self.form.total_expired = total_expired

        items = []
        for room in self.form.rooms.all():
            for manager in room.managers.all():
                status = None
                status_filtered = RequestFormStatus.objects.filter(form_id=self.form.id, room_id=room.id, manager_id=manager.id)
                if status_filtered.exists():
                    status = status_filtered

                items.append({
                    'id': self.form.id,
                    'form': self.form,
                    'room': room,
                    'areas': [area.name for area in room.areas.all()],
                    'manager': {'id': manager.id, 'full_name': manager.get_full_name()},
                    'status': status
                })

        return render(request, 'key_request/admin/view_form_details.html', {
            'form': self.form,
            'items': items,
            'req_status_dict': REQUEST_STATUS_DICT,
            'post_url': self.url,
            'tab_urls': {
                'form_details': self.url + '?t=form_details&next=' + self.next ,
                'selected_rooms': self.url + '?t=selected_rooms&next=' + self.next,
                'training_records': self.url + '?t=training_records&next=' + self.next
            },
            'tab': self.tab,
            'next': self.next
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        room_id = request.POST.get('room')
        manager_id = request.POST.get('manager')
        status = request.POST.get('status')

        if not room_id or not manager_id or not status:
            raise SuspiciousOperation

        RequestFormStatus.objects.create(
            form = self.form,
            room_id = room_id,
            manager_id = manager_id,
            operator_id = request.user.id,
            status = status
        )
        messages.success(request, 'Success! Room {0} status has been updated.'.format(room_id))
        return HttpResponseRedirect(request.POST.get('next'))


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@require_http_methods(['POST'])
def update_all(request):
    rooms = request.POST.getlist('rooms[]')
    status = request.POST.get('status')
    if not rooms:
            raise SuspiciousOperation

    if status:
        objs = []
        for room in rooms:
            room_sp = room.split('_')
            objs.append(RequestFormStatus(
                form = RequestForm.objects.get(id=room_sp[0]),
                room_id = room_sp[1],
                manager_id = room_sp[2],
                operator_id = request.user.id,
                status = status
            ))

        if len(objs) > 0:
            RequestFormStatus.objects.bulk_create(objs)
            messages.success(request, 'Success! The number of rooms ({0}) have been updated.'.format(len(objs)))
        else:
            messages.warning(request, 'There is no room to update.')
    else:
        messages.error(request, "Error! Please select the status, and try again.")

    return HttpResponseRedirect(request.POST.get('next'))


@method_decorator([never_cache], name='dispatch')
class Settings(LoginRequiredMixin, View):
    ''' This is for Building and Floor models '''

    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)
        model = GET_SETTINGS_MODEL(kwargs.get('model'))
        if not model:
            raise Http404

        self.raw_model = kwargs.get('model')
        self.model = model
        self.model_obj = apps.get_model(app_label='key_request', model_name=model)
        self.form = GET_SETTINGS_FORM(model)
        return setup

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        items = self.model_obj.objects.all()
        return render(request, 'key_request/admin/settings.html', {
            'total_items': len(items),
            'items': items,
            'headers': func.get_headers(self.model_obj),
            'form': self.form,
            'raw_model': self.raw_model,
            'model': self.model
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        form = self.form(request.POST)
        if form.is_valid():
            if form.save():
                messages.success(request, 'Successfully created {0} under {1} settings.'.format(form.cleaned_data.get('name'), self.model))
            else:
                messages.error(request, 'Error occured while creating {0} under {1} settings. Please try again.'.format(form.cleaned_data.get('name'), self.model))
        else:
            messages.error(request, 'An error occurred. Form is invalid. {0}'.format(get_error_messages(form.errors.get_json_data())))

        return redirect('key_request:settings', model=self.raw_model)


@method_decorator([never_cache], name='dispatch')
class EditSetting(LoginRequiredMixin, View):

    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)
        model = GET_SETTINGS_MODEL(kwargs.get('model'))
        if not model:
            raise Http404

        self.raw_model = kwargs.get('model')
        self.model = model
        self.model_obj = apps.get_model(app_label='key_request', model_name=model)
        self.form = GET_SETTINGS_FORM(model)
        return setup

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        id = request.POST.get('item')
        if not id:
            raise Http404

        instance = get_object_or_404(self.model_obj, id=id)
        form = self.form(request.POST, instance=instance)
        if form.is_valid():
            if form.save():
                messages.success(request, 'Successfully {0} - {1} (ID: {2}) updated'.format(self.model, instance.name, id))
            else:
                messages.error(request, 'Error occured while updating {0} - {1} (ID: {2}). Please try again.'.format(self.model, instance.name, id))
        else:
            messages.error(request, 'An error occurred. Form is invalid. {0}'.format(get_error_messages(form.errors.get_json_data())))

        return redirect('key_request:settings', model=self.raw_model)


@method_decorator([never_cache], name='dispatch')
class DeleteSetting(LoginRequiredMixin, View):

    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)
        model = GET_SETTINGS_MODEL(kwargs.get('model'))
        if not model:
            raise Http404

        self.raw_model = kwargs.get('model')
        self.model = model
        self.model_obj = apps.get_model(app_label='key_request', model_name=model)
        return setup

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        id = request.POST.get('item')
        if not id:
            raise Http404

        obj = self.model_obj.objects.filter(id=id)
        if obj.exists():
            instance = obj.first()
            obj.delete()
            messages.success(request, 'Successfully {0} - {1} (ID: {2}) deleted'.format(self.model, instance.name, id))
        else:
            messages.error(request, 'Error occured while deleting {0} - {1} (ID: {2}). Please try again.'.format(self.model, instance.name, id))

        return redirect('key_request:settings', model=self.raw_model)


@method_decorator([never_cache, access_admin_only], name='dispatch')
class AllRooms(LoginRequiredMixin, View):
    """ Display all rooms """

    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)

        if request.session.get(CREATE_ROOM_KEY):
            del request.session[CREATE_ROOM_KEY]

        if request.session.get(EDIT_ROOM_KEY):
            del request.session[EDIT_ROOM_KEY]

        return setup


    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        room_list = Room.objects.all()
        total_rooms = len(room_list)

        building = request.GET.get('building')
        floor = request.GET.get('floor')
        number = request.GET.get('number')
        if building:
            room_list = room_list.filter(building__code__icontains=building)
        if floor:
            room_list = room_list.filter(floor__name__icontains=floor)
        if number:
            room_list = room_list.filter(number__icontains=number)

        num_filtered_rooms = len(room_list)

        page = request.GET.get('page', 1)
        paginator = Paginator(room_list, 10)

        try:
            rooms = paginator.page(page)
        except PageNotAnInteger:
            rooms = paginator.page(1)
        except EmptyPage:
            rooms = paginator.page(paginator.num_pages)

        for room in rooms:
            room.manager_ids = list(room.managers.all().values_list('id', flat=True))
            room.area_ids = list(room.areas.all().values_list('id', flat=True))
            room.training_ids = list(room.trainings.all().values_list('id', flat=True))

        return render(request, 'key_request/admin/all_rooms.html', {
            'total_rooms': total_rooms,
            'num_filtered_rooms': num_filtered_rooms,
            'rooms': rooms,
            'search_filter_options': SEARCH_FILTER_OPTIONS,
            'users': User.objects.all(),
            'areas': Lab.objects.all(),
            'trainings': Cert.objects.all()
        })


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def delete_room(request):
    room_filtered = Room.objects.filter(id=request.POST.get('room'))
    if room_filtered.exists():
        room_filtered.delete()
        messages.success(request, 'Success! Room Number {0} deleted.'.format(room_filtered.first().number))
    else:
        messages.error(request, 'Error! Failed to delete Room Number {0}.'.format(room_filtered.first().number))
    return redirect('key_request:all_rooms')


@method_decorator([never_cache, access_admin_only], name='dispatch')
class EditRoom(LoginRequiredMixin, View):

    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)

        room_id = kwargs.get('room_id')
        tab = request.GET.get('t')
        next = func.get_next(request)
        if not room_id or not tab or not next:
            raise SuspiciousOperation

        self.room = get_object_or_404(Room, id=room_id)
        self.tab = tab
        self.url = reverse('key_request:edit_room', args=[room_id]) + '?t='
        self.next = next

        return setup

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        data, manager_ids, area_ids, training_ids = func.create_data_from_session(request.session, EDIT_ROOM_KEY, self.room)

        return render(request, 'key_request/admin/edit_room.html', {
            'room': self.room,
            'form': RoomForm(initial=data) if self.tab == 'basic_info' else None,
            'users': User.objects.all() if self.tab == 'pis' else None,
            'areas': Lab.objects.all() if self.tab == 'areas' else None,
            'trainings': Cert.objects.all() if self.tab == 'trainings' else None,
            'tab_urls': func.get_tab_urls(self.url, self.next),
            'tab': self.tab,
            'manager_ids': manager_ids,
            'area_ids': area_ids,
            'training_ids': training_ids,
            'next': self.next
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        method = request.POST.get('method')
        tab = request.POST.get('tab')
        next = request.POST.get('next')

        if not method or not tab or not next:
            raise SuspiciousOperation

        if 'Save' in method:
            data = {
                'building': self.room.building.id,
                'floor': self.room.floor.id,
                'number': self.room.number,
                'is_active': True if self.room.is_active else False,
                'managers': [manager.id for manager in self.room.managers.all()],
                'areas': [area.id for area in self.room.areas.all()],
                'trainings': [training.id for training in self.room.trainings.all()]
            }

            if request.session.get(EDIT_ROOM_KEY):
                data = request.session[EDIT_ROOM_KEY]

            if tab == 'basic_info':
                data['building'] = request.POST.get('building')
                data['floor'] = request.POST.get('floor')
                data['number'] = request.POST.get('number')
                data['is_active'] = True if request.POST.get('is_active') else False

            elif tab == 'pis':
                data['managers'] = func.str_to_int(request.POST.getlist('managers[]'))

            elif tab == 'areas':
                data['areas'] = func.str_to_int(request.POST.getlist('areas[]'))

            elif tab == 'trainings':
                data['trainings'] = func.str_to_int(request.POST.getlist('trainings[]'))

            request.session[EDIT_ROOM_KEY] = data

            return HttpResponseRedirect(self.url + URL_NEXT[tab] + '&next=' + next)

        elif method == 'Update Room':
            data, manager_ids, area_ids, training_ids = func.update_data_from_post_and_session(request.POST, request.session, EDIT_ROOM_KEY, tab, self.room)
            form = RoomForm(data, instance=self.room)
            if form.is_valid():
                room = form.save()
                if room:
                    room.managers.clear()
                    room.areas.clear()
                    room.trainings.clear()

                    if len(manager_ids) > 0:
                        room.managers.add(*manager_ids)

                    if len(area_ids) > 0:
                        room.areas.add(*area_ids)

                    if len(training_ids) > 0:
                        room.trainings.add(*training_ids)

                    if request.session.get(EDIT_ROOM_KEY):
                        del request.session[EDIT_ROOM_KEY]

                    messages.success(request, 'Success! {0} has been updated.'.format(func.display_room(room, 'id')))
                else:
                    messages.error(request, 'Error! Failed to update {0} for some reason. Please try again.'.format(func.display_room(room, 'id')))
            else:
                messages.error(request, 'Error! Form is invalid. {0}'.format(get_error_messages(form.errors.get_json_data())))

        return HttpResponseRedirect(next)

        # success = False
        # if tab == 'basic_info':
        #     form = RoomForm(request.POST, instance=self.room)
        #     if form.is_valid():
        #         if form.save():
        #             success = True
        #     else:
        #         messages.error(request, 'Error! Form is invalid. {0}'.format(get_error_messages(form.errors.get_json_data())))
        # elif tab == 'pis':
        #     success = update_room_data(self.room.managers, request.POST.getlist('managers[]'))
        # elif tab == 'areas':
        #     success = update_room_data(self.room.areas, request.POST.getlist('areas[]'))
        # elif tab == 'trainings':
        #     success = update_room_data(self.room.trainings, request.POST.getlist('trainings[]'))

        # if success:
        #     messages.success(request, 'Success! {1} {2} - Room {3} ({0}) has been updated.'.format(self.room.id, self.room.building.code, self.room.floor.name, self.room.number))
        # else:
        #     messages.error(request, 'Error! Failed to edit {1} {2} - Room {3} ({0}) for some reason. Please try again.'.format(self.room.id, self.room.building.code, self.room.floor.name, self.room.number))

        return HttpResponseRedirect(next)


def update_room_data(queryset, data):
    old_data = set(queryset.all().values_list('id', flat=True))
    new_data = set([int(d) for d in data])
    if old_data != new_data:
        common = old_data.intersection(new_data)
        if len(common) == 0:
            queryset.remove(*old_data)
            queryset.add(*new_data)
        else:
            old_diff = old_data.difference(common)
            if len(old_diff) > 0:
                queryset.remove(*old_diff)

            new_diff = new_data.difference(common)
            if len(new_diff) > 0:
                queryset.add(*new_diff)
    return True


@method_decorator([never_cache, access_admin_only], name='dispatch')
class CreateRoom(LoginRequiredMixin, View):
    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)

        tab = request.GET.get('t')
        if not tab:
            raise SuspiciousOperation

        self.tab = tab
        self.url = reverse('key_request:create_room') + '?t='

        return setup

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        data, manager_ids, area_ids, training_ids = func.create_data_from_session(request.session, CREATE_ROOM_KEY)
        print(data)
        return render(request, 'key_request/admin/create_room.html', {
            'form': RoomForm(initial=data) if self.tab == 'basic_info' else None,
            'users': User.objects.all() if self.tab == 'pis' else None,
            'areas': Lab.objects.all() if self.tab == 'areas' else None,
            'trainings': Cert.objects.all() if self.tab == 'trainings' else None,
            'tab_urls': func.get_tab_urls(self.url),
            'tab': self.tab,
            'manager_ids': manager_ids,
            'area_ids': area_ids,
            'training_ids': training_ids
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        method = request.POST.get('method')
        tab = request.POST.get('tab')

        if not method or not tab:
            raise SuspiciousOperation

        if 'Save' in method:
            data = {
                'building': '',
                'floor': '',
                'number': '',
                'is_active': None,
                'managers': [],
                'areas': [],
                'trainings': []
            }

            if request.session.get(CREATE_ROOM_KEY):
                data = request.session[CREATE_ROOM_KEY]

            if tab == 'basic_info':
                data['building'] = request.POST.get('building')
                data['floor'] = request.POST.get('floor')
                data['number'] = request.POST.get('number')
                data['is_active'] = True if request.POST.get('is_active') else False

            elif tab == 'pis':
                data['managers'] = func.str_to_int(request.POST.getlist('managers[]'))

            elif tab == 'areas':
                data['areas'] = func.str_to_int(request.POST.getlist('areas[]'))

            elif tab == 'trainings':
                data['trainings'] = func.str_to_int(request.POST.getlist('trainings[]'))

            request.session[CREATE_ROOM_KEY] = data


            return HttpResponseRedirect(self.url + URL_NEXT[tab])

        elif method == 'Create Room':
            data, manager_ids, area_ids, training_ids = func.update_data_from_post_and_session(request.POST, request.session, CREATE_ROOM_KEY, tab)
            form = RoomForm(data)
            if form.is_valid():
                room = form.save()
                if room:
                    if len(manager_ids) > 0:
                        room.managers.add(*manager_ids)

                    if len(area_ids) > 0:
                        room.areas.add(*area_ids)

                    if len(training_ids) > 0:
                        room.trainings.add(*training_ids)

                    if request.session.get(CREATE_ROOM_KEY):
                        del request.session[CREATE_ROOM_KEY]

                    messages.success(request, 'Success! {0} has been created.'.format(func.display_room(room)))
                else:
                    messages.error(request, 'Error! Failed to create {0} for some reason. Please try again.'.format(func.display_room(room)))
            else:
                messages.error(request, 'Error! Form is invalid. {0}'.format(get_error_messages(form.errors.get_json_data())))

        return HttpResponseRedirect(self.url + 'basic_info')


# Manager Dashboard

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
            'search_filter_options': SEARCH_FILTER_OPTIONS,
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

        RequestFormStatus.objects.create(
            form_id = form_id,
            room_id = room_id,
            manager_id = manager_id,
            operator_id = request.user.id,
            status = status
        )
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
            'search_filter_options': SEARCH_FILTER_OPTIONS
        })


# Helpers

def GET_SETTINGS_MODEL(model):
    dict = {
        'buildings': 'Building',
        'floors': 'Floor'
    }

    return dict[model] if model in dict.keys() else None


def GET_SETTINGS_FORM(model):
    dict = {
        'Building': BuildingForm,
        'Floor': FloorForm
    }
    return dict[model] if model in dict.keys() else None


def SEARCH_FILTER_OPTIONS():
    return {
        'buildings': Building.objects.values('code').distinct(),
        'floors': Floor.objects.values('name').distinct(),
        'rooms': Room.objects.values('number').distinct()
    }
