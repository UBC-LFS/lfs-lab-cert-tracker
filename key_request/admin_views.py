from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, Http404, JsonResponse, QueryDict
from django.utils.html import format_html
from django.db.utils import IntegrityError

from django.db.models import Q, Case, When, IntegerField, Value

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.urls import reverse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.contrib.auth.models import User
from django.core.exceptions import SuspiciousOperation
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.apps import apps

from lfs_lab_cert_tracker.models import Lab, Cert
from app.accesses import access_admin_only, access_pi_admin_key_request
from app import functions as appFunc
from app.utils import NUM_PER_PAGE

from .models import Room, Group, UserGroup
from .forms import BuildingForm, FloorForm, RoomForm, RequestForm, RequestFormStatus, GroupForm
from .mixins import RoomActionsMixin
from . import functions as func
from .utils import REQUEST_STATUS_DICT, CREATE_ROOM_KEY, EDIT_ROOM_KEY, URL_NEXT, UserRole

import json


@method_decorator([never_cache, access_admin_only], name='dispatch')
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
            'search_filter_options': func.search_filter_options,
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


@method_decorator([never_cache, access_admin_only], name='dispatch')
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
        next = request.POST.get('next')

        if not status:
            messages.error(request, 'Error: A status must be selected.')
            if next:
                return HttpResponseRedirect(next)
            else:
                return redirect('key_request:index')
        
        if not self.form or not room_id or not manager_id or not next:
            raise SuspiciousOperation

        RequestFormStatus.objects.create(
            form_id = self.form.id,
            room_id = room_id,
            manager_id = manager_id,
            operator_id = request.user.id,
            status = status
        )

        room = Room.objects.get(id=room_id)

        # Check if the admin is approving of behalf of another manager
        absent_pi = manager_id if int(manager_id) != int(request.user.id) else None

        func.count_approved_numbers_by_id(status, self.form, room, request.user.id, absent_pi)

        messages.success(request, 'Success! The status of {0} has been updated.'.format(func.display_room(room)))
        return HttpResponseRedirect(next)


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_pi_admin_key_request
@require_http_methods(['POST'])
def update_all(request):
    rooms = request.POST.getlist('rooms[]')
    status = request.POST.get('status')
    if not rooms:
            raise SuspiciousOperation

    if status:
        objs = []
        manager_room_map = {}
        for room in rooms:
            room_sp = room.split('_')
            form = RequestForm.objects.get(id=room_sp[0])
            objs.append(RequestFormStatus(
                form = form,
                room_id = room_sp[1],
                manager_id = room_sp[2],
                operator_id = request.user.id,
                status = status
            ))

            manager_id = room_sp[2]

            manager_room_map.setdefault(manager_id, []).append(room_sp[1])

        if len(objs) > 0:
            request_status_forms = RequestFormStatus.objects.bulk_create(objs)
            func.count_approved_numbers_by_id_multiple_rooms(status, request_status_forms, request.user.id, manager_room_map)

            messages.success(request, 'Success! The number of rooms ({0}) have been updated.'.format(len(objs)))
        else:
            messages.warning(request, 'There is no room to update.')
    else:
        messages.error(request, "Error! Please select the status, and try again.")

    return HttpResponseRedirect(request.POST.get('next'))


@method_decorator([never_cache, access_admin_only], name='dispatch')
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
            messages.error(request, 'An error occurred. Form is invalid. {0}'.format(appFunc.get_error_messages(form.errors.get_json_data())))

        return redirect('key_request:settings', model=self.raw_model)


@method_decorator([never_cache, access_admin_only], name='dispatch')
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
            messages.error(request, 'An error occurred. Form is invalid. {0}'.format(appFunc.get_error_messages(form.errors.get_json_data())))

        return redirect('key_request:settings', model=self.raw_model)


@method_decorator([never_cache, access_admin_only], name='dispatch')
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
            try:
                obj.delete()
                messages.success(request, 'Successfully {0} - {1} (ID: {2}) deleted'.format(self.model, instance.name, id))
            except IntegrityError:
                msg = "Cannot delete {0} - {1} while it is still associated with rooms. ".format(self.model, instance.name)
                model = str(self.model).lower()
                filter = instance.name if model != 'building' else instance.code
                msg += format_html('<a href="{0}">Click</a> to see all associated rooms.', reverse('key_request:all_rooms') + '?' + model + '=' + filter)
                messages.error(request, msg)
        else:
            messages.error(request, 'Error occurred while deleting {0} (ID: {1}). Please try again.'.format(self.model, id))

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
            'search_filter_options': func.search_filter_options,
            'users': User.objects.all(),
            'areas': Lab.objects.all(),
            'trainings': Cert.objects.all()
        })


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
                'key': None,
                'fob': None,
                'alarm': None,
                'is_active': None,
                'note': None,
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
                data['key'] = True if request.POST.get('key') else False
                data['fob'] = True if request.POST.get('fob') else False
                data['alarm'] = True if request.POST.get('alarm') else False
                data['is_active'] = True if request.POST.get('is_active') else False
                data['note'] = request.POST.get('note')

            elif tab == 'pis':
                data['managers'] = func.str_to_int(request.POST.getlist('managers[]'))

            elif tab == 'areas':
                data['areas'] = func.str_to_int(request.POST.getlist('areas[]'))

            elif tab == 'trainings':
                data['trainings'] = func.str_to_int(request.POST.getlist('trainings[]'))

            print(data)
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
                messages.error(request, 'Error! Form is invalid. {0}'.format(appFunc.get_error_messages(form.errors.get_json_data())))

        return HttpResponseRedirect(self.url + 'basic_info')


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
                'key': True if self.room.is_active else False,
                'fob': True if self.room.is_active else False,
                'alarm': True if self.room.is_active else False,
                'is_active': True if self.room.is_active else False,
                'note': self.room.note,
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
                data['key'] = True if request.POST.get('key') else False
                data['fob'] = True if request.POST.get('fob') else False
                data['alarm'] = True if request.POST.get('alarm') else False
                data['is_active'] = True if request.POST.get('is_active') else False
                data['note'] = request.POST.get('note')

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
                messages.error(request, 'Error! Form is invalid. {0}'.format(appFunc.get_error_messages(form.errors.get_json_data())))

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

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def delete_room(request):
    room_filtered = Room.objects.filter(id=request.POST.get('room'))
    room_number = room_filtered.first().number
    room_building = room_filtered.first().building.code
    room_floor = room_filtered.first().floor.name
    if room_filtered.exists():
        try:
            room_filtered.delete()
            messages.success(request, 'Success! Room Number {0} deleted.'.format(room_number))
        except IntegrityError:
            msg = "Cannot delete {0} {1} {2} as there are associated key requests. ".format(room_building, room_floor, room_number)
            msg += format_html('<a href="{0}">Click</a> to see all associated requests.',
                               reverse('key_request:all_requests') + '?building=' + room_building +
                               '&floor=' + room_floor + '&number=' + room_number)
            messages.error(request, msg)
    else:
        messages.error(request, 'Error! Failed to delete Room Number {0}.'.format(room_number))
    return redirect('key_request:all_rooms')

@method_decorator([never_cache, access_admin_only], name='dispatch')
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

@method_decorator([never_cache, access_admin_only], name='dispatch')
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

# ROOM GROUPS START

@method_decorator([never_cache, access_admin_only], name='dispatch')
class ViewRoomGroups(LoginRequiredMixin, View):

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        all_groups = func.get_all_groups_of_type(type=Group.GroupType.LAB)
        total_groups = all_groups.count()

        if total_groups == 0:
            return render(request, 'key_request/admin/all_groups.html', {
                'total_groups': 0,
                'num_filtered_groups': 0,
                'groups': [],
            })

        selected_ids = request.GET.getlist('members[]', [])
        if selected_ids:
            all_groups = func.get_groups_with_matching_composition(selected_ids, Group.GroupType.LAB)

        group_name = request.GET.get('name')
        member_first_name = request.GET.get('member_first_name')
        member_last_name = request.GET.get('member_last_name')
        room_pk = request.GET.get('room_pk')

        if group_name:
            all_groups = all_groups.filter(name__icontains=group_name)
        if member_first_name:
            all_groups = all_groups.filter(usergroup__user__first_name__icontains=member_first_name).distinct()
        if member_last_name:
            all_groups = all_groups.filter(usergroup__user__last_name__icontains=member_last_name).distinct()
        if room_pk:
            all_groups = all_groups.filter(manager_groups__pk=room_pk).distinct()

        num_filtered_groups = all_groups.count()

        page = request.GET.get('page', 1)
        paginator = Paginator(all_groups, 10)

        try:
            groups = paginator.page(page)
        except PageNotAnInteger:
            groups = paginator.page(1)
        except EmptyPage:
            groups = paginator.page(paginator.num_pages)


        return render(request, 'key_request/admin/all_groups.html', {
            'total_groups': total_groups,
            'num_filtered_groups': num_filtered_groups,
            'user_roles': {
                'PRINCIPAL_INVESTIGATOR': UserRole.PRINCIPAL_INVESTIGATOR,
                'PI_PROXY': UserRole.PI_PROXY,
                'LAB_USER': UserRole.LAB_USER,
            },
            'groups': groups,
        })

@method_decorator([never_cache, access_admin_only], name='dispatch')
class CreateRoomGroup(LoginRequiredMixin, View):

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        return render(request, 'key_request/admin/create_group.html', {
            'form': GroupForm(autofill_url=reverse('key_request:user_autofill')),
            'validate_group_url': reverse('key_request:validate_room_group'),
            'user_roles_json': json.dumps(UserRole.CHOICES),
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):

        form = GroupForm(request.POST)
        if form.is_valid():
            id_list = form.cleaned_data['member_ids']

            group_name = form.cleaned_data['name']
            role_list = request.POST.get('member_roles', '').split(',')
            group = func.create_group_from_ids_list(group_name, Group.GroupType.LAB, id_list, role_list)

            messages.success(request, 'Success! {0} has been created.'.format(group.name))

        else:
            messages.error(request, 'Error! Form is invalid. {0}'.format(appFunc.get_error_messages(form.errors.get_json_data())))

        return HttpResponseRedirect(reverse('key_request:all_groups'))

@method_decorator([never_cache, access_admin_only], name='dispatch')
class EditRoomGroups(LoginRequiredMixin, View):

    def setup(self, request, *args, **kwargs):

        setup = super().setup(request, *args, **kwargs)
        group_id = kwargs.get('group_id')

        try:
            self.group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            self.group = None

        return setup

    def _make_member_string(self):
        member_ids = func.get_group_member_ids(self.group)
        return ','.join(member_ids)

    def _make_member_dict(self):
        user_groups = UserGroup.objects.filter(group=self.group).select_related('user')
        return [
            {
                'first_name': ug.user.first_name,
                'last_name': ug.user.last_name,
                'role': ug.role,
                'id': ug.user.id
            } for ug in user_groups
        ]


    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        if not self.group:
            messages.error(request, 'Error! No group matches the id specified. It may have been deleted.')
            return HttpResponseRedirect(reverse('key_request:all_groups'))


        return render(request, 'key_request/admin/edit_group.html', {
            'form': GroupForm(
                autofill_url=reverse('key_request:user_autofill'),
                initial={
                    'member_ids': self._make_member_string(),
                    'name': self.group.name}
            ),
            'validate_group_url': reverse('key_request:validate_room_group'),
            'group': self.group,
            'group_members': func.get_group_members(self.group),
            'group_members_dict': self._make_member_dict(),
            'user_roles_json': json.dumps(UserRole.CHOICES),
        })


    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        form = GroupForm(request.POST, instance=self.group)
        if form.is_valid():
            group_name = form.cleaned_data['name']

            id_list = form.cleaned_data['member_ids']
            role_list = request.POST.get('member_roles', '').split(',')
            id_role_pairs = zip(id_list, role_list)

            users_by_id = User.objects.in_bulk(id_list)

            UserGroup.objects.filter(group=self.group).delete()

            for user_id, role in id_role_pairs:
                user = users_by_id.get(int(user_id))
                if user:
                    UserGroup.objects.create(group=self.group, user=user, role=int(role))

            self.group.name = group_name
            self.group.save()

            messages.success(request, 'Success! {0} has been updated.'.format(self.group.name))

        else:
            messages.error(request, 'Error! Form is invalid. {0}'.format(appFunc.get_error_messages(form.errors.get_json_data())))

        return HttpResponseRedirect(reverse('key_request:all_groups'))

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['GET'])
def user_autofill_suggestions(request):
    name_q = request.GET.get('name_q', '')

    users = (User.objects
    .filter(
        Q(first_name__icontains=name_q) | Q(last_name__icontains=name_q)
    ).annotate(
        priority=Case(
            When(first_name__startswith=name_q, then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        )
    )).order_by('priority', 'first_name', 'last_name')
    data = [
        {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name
        } for user in users
    ]

    return JsonResponse({'data' : data}, status=200)

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['GET'])
def validate_room_group(request):
    group_id = request.GET.get('group_id', None)
    selected_name = request.GET.get('name', '').strip()
    selected_ids = request.GET.getlist('members[]', [])

    if group_id:
        try:
            group_id = int(group_id)
        except ValueError:
            group_id = None

    # First checks name, then if no match, checks group composition

    name_matches = func.get_group_with_matching_name(selected_name, group_id)
    if name_matches.exists():
        # name is a unique field
        matching_group = name_matches.first()
        q = QueryDict(mutable=True)
        q.setlist('members[]', [matching_group.id])
        view_url = reverse('key_request:all_groups') + "?" + q.urlencode()

        group_member_names = [
            ug.user.get_full_name()
            for ug in UserGroup.objects.filter(group=matching_group).select_related('user')
        ]


        return JsonResponse({
            'has_duplicate': True,
            'match_type': 'name',
            'data': {
                'view_url': view_url,
                'group_members': group_member_names,
                'group_members_string': ", ".join(group_member_names)
            }},
            status=200
        )

    group_matches = func.get_groups_with_matching_composition(selected_ids, Group.GroupType.LAB, group_id)

    if group_matches.exists():
        num_matches = group_matches.count()
        q = QueryDict(mutable=True)
        q.setlist('members[]', selected_ids)
        view_url = reverse('key_request:all_groups') + "?" + q.urlencode()

        group_names = [group.name for group in group_matches]

        return JsonResponse({
            'has_duplicate': True,
            'match_type': 'composition',
            'data': {
                'num_matches': num_matches,
                'view_url': view_url,
                'group_names': group_names,
            }},
            status=200
        )
    else:
        return JsonResponse({
            'has_duplicate': False,
            'match_type': None,
            'data': None
            },
            status=200
        )

@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_admin_only
@require_http_methods(['POST'])
def delete_group(request):
    id = request.POST.get('group')
    try:
        group = Group.objects.get(id=id)
        group_name = group.name
        group.delete()
        messages.success(request, 'Success! Lab Room Group {0} has been deleted.'.format(group_name))
    except Group.DoesNotExist:
        messages.error(request, 'Error! Failed to delete Lab Room Group Number {0}. It may have already been deleted.'.format(id))
    return redirect('key_request:all_groups')
# ROOM GROUPS END


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