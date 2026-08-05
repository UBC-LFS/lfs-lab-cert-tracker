from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, Http404, JsonResponse, QueryDict
from django.utils.html import format_html
from django.db.utils import IntegrityError
from django.db.models.functions import Concat
from django.db.models import Q, Case, When, IntegerField, Value, Exists, OuterRef

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
from django.core.mail import send_mail
from django.core.validators import validate_email

from lfs_lab_cert_tracker.models import Lab, Cert
from app.accesses import access_admin_only, access_pi_admin_key_request, access_group_coordinator_admin_key_request
from app import functions as appFunc
from app.utils import NUM_PER_PAGE
from .email_coordinator import ApprovalNotificationManager

from .models import Room, ApprovalGroup, ApprovalGroupRole
from .forms import BuildingForm, FloorForm, RoomForm, RequestForm, RequestFormStatus, ApprovalGroupForm
from .models import Room, UserFilter, RoomEmail
from .forms import BuildingForm, FloorForm, RoomForm, RequestForm, RequestFormStatus
from .mixins import RoomActionsMixin
from . import functions as func
from .dashboard_coordinators import DashboardCoordinator, RequestFormProcessor, ExpiredRequestFormProcessor
from .utils import REQUEST_STATUS_DICT, CREATE_ROOM_KEY, EDIT_ROOM_KEY, URL_NEXT, APPROVED

GROUPS_PER_PAGE = 10

@method_decorator([never_cache, access_admin_only], name='dispatch')
class AllRequests(LoginRequiredMixin, View):

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        method = request.GET.get('method', None)

        query = {
            'building': request.GET.get('building'),
            'floor': request.GET.get('floor'),
            'number': request.GET.get('number'),
            'room': request.GET.get('room'),
            'name': request.GET.get('name'),
            'status': request.GET.get('status')
        }

        if method == 'save':
            user_filter = UserFilter.objects.filter(user_id=request.user.id)
            if user_filter.exists():
                user_filter.update(json = query)
                messages.success(request, 'Your filter has been updated successfully.')
            else:
                UserFilter.objects.create(user=request.user, json=query)
                messages.success(request, 'Your filter has been saved successfully.')

            # Create a new url
            query_params = request.GET.copy()
            query_params.pop('method', None)
            encoded_params = query_params.urlencode()
            base_url = request.path
            new_url = f"{base_url}?{encoded_params}" if encoded_params else base_url

            return redirect(new_url)

        coordinator = DashboardCoordinator(request.user, query, [RequestFormProcessor])
        coordinator.run()

        form_list = coordinator.get_forms()

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
            'total_forms': coordinator.get_total_forms(),
            'num_filtered_forms': coordinator.get_num_filtered_forms(),
            'forms': forms,
            'num_new_forms': coordinator.get_num_new_forms(),
            'req_status_dict': REQUEST_STATUS_DICT,
            'search_filter_options': func.search_filter_options,
            'is_admin': True if request.user.is_superuser else False
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        form_id = request.POST.get('form')
        manager_id = request.POST.get('manager_id', None)
        group_id = request.POST.get('group_id', None)
        operator = appFunc.get_user_name(request.user)
        status = request.POST.get('status')
        fs = RequestFormStatus.objects.create(form_id=form_id, operator=operator, manager_id=manager_id, group_id=group_id, status=status)
        if fs:
            messages.success(request, "Success! {0}'s status has been updated.".format(operator))
        else:
            messages.error(request, "Error! Failed to update {0}'s status for some reason. Please try again.".format(operator))
        return HttpResponseRedirect(request.POST.get('next'))


@method_decorator([never_cache, access_admin_only], name='dispatch')
class ExpiredRequests(LoginRequiredMixin, View):

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

        coordinator = DashboardCoordinator(request.user, query, [ExpiredRequestFormProcessor])
        coordinator.run()

        form_list = coordinator.get_forms()

        page = request.GET.get('page', 1)
        paginator = Paginator(form_list, NUM_PER_PAGE)

        try:
            forms = paginator.page(page)
        except PageNotAnInteger:
            forms = paginator.page(1)
        except EmptyPage:
            forms = paginator.page(paginator.num_pages)

        return render(request, 'key_request/admin/expired_requests.html', {
            'total_forms': coordinator.get_total_forms(),
            'num_filtered_forms': coordinator.get_num_filtered_forms(),
            'forms': forms,
            'req_status_dict': REQUEST_STATUS_DICT,
            'search_filter_options': func.search_filter_options,
            'is_admin': True if request.user.is_superuser else False
        })


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
        rooms = set()

        # Need both the managers and the groups

        all_approved = True

        for room in self.form.rooms.all():
            rooms.add(room)

            areas = [area.name for area in room.areas.all()]

            managers = room.managers.all()
            groups = room.groups.all()
            if not managers and not groups:
                items.append({
                    'id': self.form.id,
                    'label': None,
                    'form': self.form,
                    'room': room,
                    'areas': areas,
                    # For sorting the list. Rooms without a managing entity are placed at the end
                    'priority': 2,
                    'sorting_key': f"{room.building.name}{room.floor.name}{room.number}"
                })
                all_approved = False
            else:
                manager_forms, manager_all_approved = self._create_item_with_entity_status(room, areas, 'manager', managers, 0)
                group_forms, group_all_approved = self._create_item_with_entity_status(room, areas, 'group', groups, 1)
                items += manager_forms + group_forms
                all_approved &= manager_all_approved and group_all_approved

        items = sorted(items, key=lambda x: (x['priority'], x['sorting_key']), reverse=False)
        self.form.all_approved = all_approved

        return render(request, 'key_request/admin/view_form_details.html', {
            'form': self.form,
            'rooms': list(rooms),
            'items': items,
            'req_status_dict': REQUEST_STATUS_DICT,
            'post_url': self.url,
            'tab_urls': {
                'form_details': self.url + '?t=form_details&next=' + self.next ,
                'selected_rooms': self.url + '?t=selected_rooms&next=' + self.next,
                'training_records': self.url + '?t=training_records&next=' + self.next,
                'emails': self.url + '?t=emails&next=' + self.next
            },
            'tab': self.tab,
            'next': self.next
        })

    def _create_item_with_entity_status(self, room, areas, entity_label, entities, priority):
        items = []
        if entity_label not in ['group', 'manager']:
            return []

        entity_filter_label = f"{entity_label}_id"

        all_approved = True

        for entity in entities:
            entity_filter = {
                entity_filter_label: entity.id
            }
            status_filtered = RequestFormStatus.objects.filter(form_id=self.form.id, room_id=room.id, **entity_filter).order_by('-created_at')
            is_new = not status_filtered.exists()
            status = status_filtered

            if is_new:
                status = None

            if not status or status.first().status != APPROVED:
                all_approved = False


            if entity_label == 'group':
                sorting_key = entity.name

            if entity_label == 'manager':
                sorting_key = entity.get_full_name()

            items.append({
                'id': self.form.id,
                'label': f'{entity_label.capitalize()} Form',
                'form': self.form,
                'room': room,
                'areas': areas,
                 entity_label: entity,
                'status': status,
                'is_new': is_new,
                # Update all expects the format: <entity_label>:<entity_id>__<form.id>:<room_id>
                'request_form_identifier': func.make_request_form_identifier(room, self.form, entity_filter_label, entity.id),
                # For sorting the list of PI/Group (PI=prio_1; group=prio_2); sorting key is then name/get_full_name()
                'priority': priority,
                'sorting_key': sorting_key
            })
        return items, all_approved


    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        room_id = request.POST.get('room')
        manager_id = request.POST.get('manager_id', None)
        group_id = request.POST.get('group_id', None)

        status = request.POST.get('status')
        next = request.POST.get('next')

        if not status:
            messages.error(request, 'Error: A status must be selected.')
            if next:
                return HttpResponseRedirect(next)
            else:
                return redirect('key_request:index')

        if not self.form or not room_id or (not manager_id and not group_id) or not next:
            raise SuspiciousOperation

        rfs = RequestFormStatus.objects.create(
            form_id = self.form.id,
            room_id = room_id,
            manager_id = manager_id,
            group_id = group_id,
            operator_id = request.user.id,
            status = status
        )

        room = Room.objects.get(id=room_id)

        email_coordinator = ApprovalNotificationManager([rfs], status, request.user)
        email_coordinator.send_email_notification()

        messages.success(request, 'Success! The status of {0} has been updated.'.format(func.display_room(room)))
        return HttpResponseRedirect(next)


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_pi_admin_key_request
@require_http_methods(['POST'])
def send_emails(request):
    user_id = request.POST.get('user_id', None)
    room_id = request.POST.get('room_id', None)
    expiry_date = request.POST.get('expiry_date', '')
    email_type = request.POST.get('email_type', None)
    next = request.POST.get('next', None)

    if not user_id or not room_id or not email_type or not next:
        raise SuspiciousOperation

    user = get_object_or_404(User, id=user_id)
    room = get_object_or_404(Room, id=room_id)
    sent = send(user, room, email_type, expiry_date)
    if sent:
        messages.success(request, 'Success! An email has been sent.')
    else:
        messages.error(request, 'An error occurred. Failed to send an email.')

    return HttpResponseRedirect(next)


def send(user, room, email_type, expiry_date):
    room_name = func.display_room(room)

    title = ''
    message = ''
    if email_type == 'key':
        title = 'Your key request for {0} has been sent to UBC Keydesk'.format(room_name)
        message = '''\
<div>
<p>Hi {0},</p>
<p>Your key request for {1} has been sent to UBC Keydesk. You will receive a notification email from UBC Keydesk when the key is ready for pickup. If you require further assistance, please email <a href="mailto:lfs.access@ubc.ca">lfs.access@ubc.ca</a>.</p>
<p>Best regards,</p>
<p>LFS Training Record Management System</p>
</div>'''.format(user.get_full_name(), room_name)

    elif email_type == 'fob':
        title = 'Your fob request is set up for {0}'.format(room_name)
        message = '''\
<div>
<p>Hi {0},</p>
<p>Your fob request is set up for {1} with an expiry date {2}. Thanks. If you require further assistance, please email <a href="mailto:lfs.access@ubc.ca">lfs.access@ubc.ca</a>.</p>
<p>Best regards,</p>
<p>LFS Training Record Management System</p>
</div>'''.format(user.get_full_name(), room_name, expiry_date)

    elif email_type == 'alarm':
        title = 'Your fob request is set up for {0}'.format(room_name)
        message = '''\
<div>
<p>Hi {0},</p>
<p>Your alarm code request is set up for {1} with an expiry date {2}.</p>
<p>If you require further assistance, please email <a href="mailto:lfs.access@ubc.ca">lfs.access@ubc.ca</a>.</p>
<p>Best regards,</p>
<p>LFS Training Record Management System</p>
</div>'''.format(user.get_full_name(), room_name, expiry_date)

    sent = send_mail(title, message, settings.EMAIL_FROM, [ user.email ], fail_silently=False, html_message=message)

    if sent:
        msg = '<p>{0}</p><hr />{1}'.format(title, message)
        RoomEmail.objects.create(user=user, room=room, type=email_type, message=msg)
        return True
    return False




@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_pi_admin_key_request
@require_http_methods(['POST'])
def update_all(request):

    raw_rooms = request.POST.getlist('rooms[]')

    status = request.POST.get('status')
    if not raw_rooms:
        raise SuspiciousOperation

    if status:
        rfs = []
        for raw_room in raw_rooms:
            # rooms in the format: <entity_label>:<entity_id>__<form.id>:<room_id>

            room_sp = raw_room.split('__')
            entity_tuple = room_sp[0].split(":")
            entity_label = entity_tuple[0]
            entity_id = entity_tuple[1]

            room_form_tuple = room_sp[1].split(":")
            form_id = room_form_tuple[0]
            room_id = room_form_tuple[1]

            form = RequestForm.objects.get(id=form_id)
            rfs_obj = RequestFormStatus(
                form = form,
                room_id = room_id,
                operator_id = request.user.id,
                status = status
            )
            setattr(rfs_obj, entity_label, entity_id)

            rfs.append(rfs_obj)


        if len(rfs) > 0:

            request_status_forms = RequestFormStatus.objects.bulk_create(rfs)

            email_coordinator = ApprovalNotificationManager(request_status_forms, status, request.user)
            email_coordinator.send_email_notification()


            messages.success(request, 'Success! The number of key request forms ({0}) have been updated.'.format(len(request_status_forms)))
        else:
            messages.warning(request, 'There are no key request forms to update.')
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
            room.groups.all().values_list('id', flat=True)
            room.manager_ids = list(room.managers.all().values_list('id', flat=True))
            room.area_ids = list(room.areas.all().values_list('id', flat=True))
            room.training_ids = list(room.trainings.all().values_list('id', flat=True))

        return render(request, 'key_request/admin/all_rooms.html', {
            'total_rooms': total_rooms,
            'num_filtered_rooms': num_filtered_rooms,
            'rooms': rooms,
            'search_filter_options': func.search_filter_options,
            'users': User.objects.all(),
            'groups': ApprovalGroup.objects.all(),
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
        data, manager_ids, group_ids, area_ids, training_ids = func.create_data_from_session(request.session, CREATE_ROOM_KEY)

        return render(request, 'key_request/admin/create_room.html', {
            'form': RoomForm(initial=data) if self.tab == 'basic_info' else None,
            'users': User.objects.all() if self.tab == 'pis' else None,
            'room_groups': ApprovalGroup.objects.filter(is_active=True) if self.tab == 'pis' else None,
            'areas': Lab.objects.all().prefetch_related('labcert_set') if self.tab == 'areas' else None,
            'trainings': Cert.objects.all() if self.tab == 'trainings' else None,
            'tab_urls': func.get_tab_urls(self.url),
            'tab': self.tab,
            'manager_ids': manager_ids,
            'group_ids': group_ids,
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
                'groups': [],
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
                data['groups'] = func.str_to_int(request.POST.getlist('groups[]'))

            elif tab == 'areas':
                original_areas = data['areas']
                data['areas'] = func.str_to_int(request.POST.getlist('areas[]'))
                data['trainings'] = func.adjust_trainings_from_added_removed_areas(data['trainings'], original_areas, data['areas'])

            elif tab == 'trainings':
                data['trainings'] = func.str_to_int(request.POST.getlist('trainings[]'))

            request.session[CREATE_ROOM_KEY] = data


            return HttpResponseRedirect(self.url + URL_NEXT[tab])

        elif method == 'Create Room':
            # Need the original areas pre-update to see which areas removed
            original_area_ids = func.get_area_ids_from_session(request.session, CREATE_ROOM_KEY)

            data, manager_ids, group_ids, area_ids, training_ids = func.update_data_from_post_and_session(request.POST, request.session, CREATE_ROOM_KEY, tab)
            if tab == 'areas':
                # If creating from the areas tab, the trainings may not be updated; maintain carry over behaviour even on create
                training_ids = func.adjust_trainings_from_added_removed_areas(training_ids, original_area_ids, area_ids)

            form = RoomForm(data)
            if form.is_valid():
                room = form.save()
                if room:
                    if len(manager_ids) > 0:
                        room.managers.add(*manager_ids)

                    if len(group_ids) > 0:
                        room.groups.add(*group_ids)

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

    def _make_conflict_map(self, group_ids, manager_ids):
        # no distinct; want dupes
        groups_members = ApprovalGroupRole.objects.filter(group_id__in=group_ids)

        conflict_map = dict()

        managers = User.objects.filter(id__in=manager_ids)

        for manager in managers:
            conflict_map.setdefault(manager, []).append("PI")

        for member in groups_members:
            conflict_map.setdefault(member.user, []).append(member.group.name)

        return dict(
            sorted(
                conflict_map.items(),
                key=lambda item: item[0].first_name
            )
        )

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        data, manager_ids, group_ids, area_ids, training_ids = func.create_data_from_session(request.session, EDIT_ROOM_KEY, self.room)
        
        return render(request, 'key_request/admin/edit_room.html', {
            'room': self.room,
            'form': RoomForm(initial=data) if self.tab == 'basic_info' else None,
            'users': User.objects.all() if self.tab == 'pis' else None,
            'room_groups': ApprovalGroup.objects.filter(is_active=True) if self.tab == 'pis' else None,
            'areas': Lab.objects.all().prefetch_related('labcert_set') if self.tab == 'areas' else None,
            'trainings': Cert.objects.all() if self.tab == 'trainings' else None,
            'tab_urls': func.get_tab_urls(self.url, self.next),
            'tab': self.tab,
            'conflict_map': self._make_conflict_map(group_ids, manager_ids) if self.tab == 'pis' else None,
            'manager_ids': manager_ids,
            'group_ids': group_ids,
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
                'key': True if self.room.key else False,
                'fob': True if self.room.fob else False,
                'alarm': True if self.room.alarm else False,
                'is_active': True if self.room.is_active else False,
                'note': self.room.note,
                'managers': [manager.id for manager in self.room.managers.all()],
                'groups': [group.id for group in self.room.groups.all()],
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
                data['groups'] = func.str_to_int(request.POST.getlist('groups[]'))


            elif tab == 'areas':
                original_areas = data['areas']
                data['areas'] = func.str_to_int(request.POST.getlist('areas[]'))
                data['trainings'] = func.adjust_trainings_from_added_removed_areas(data['trainings'], original_areas, data['areas'])


            elif tab == 'trainings':
                data['trainings'] = func.str_to_int(request.POST.getlist('trainings[]'))

            request.session[EDIT_ROOM_KEY] = data

            return HttpResponseRedirect(self.url + URL_NEXT[tab] + '&next=' + next)

        elif method == 'Update Room':

            # Need pre-update area ids for updating areas if on areas tab
            original_area_ids = func.get_area_ids_from_session(request.session, EDIT_ROOM_KEY, self.room)

            data, manager_ids, group_ids, area_ids, training_ids = func.update_data_from_post_and_session(request.POST, request.session, EDIT_ROOM_KEY, tab, self.room)

            # Only alter if the original areas have changed
            if tab == 'areas':
                # If creating from the areas tab, the trainings may not be updated;
                # maintain carry over behaviour even on create
                training_ids = func.adjust_trainings_from_added_removed_areas(training_ids, original_area_ids, area_ids)


            form = RoomForm(data, instance=self.room)
            if form.is_valid():
                room = form.save()
                if room:
                    room.managers.clear()
                    room.groups.clear()
                    room.areas.clear()
                    room.trainings.clear()

                    if len(manager_ids) > 0:
                        room.managers.add(*manager_ids)

                    if len(group_ids) > 0:
                        room.groups.add(*group_ids)

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
                messages.success(request, 'Success! The required training has been deleted from {0} room(s).'.format(count))
            else:
                messages.warning(request, 'Warning! There is no room to delete.')
        else:
            messages.error(request, "Error! Please select the Required Training, and try again.")

        return HttpResponseRedirect(request.POST.get('next'))

# GROUPS START

@method_decorator([never_cache], name='dispatch')
class ViewApprovalGroups(LoginRequiredMixin, View):

    def setup(self, request, *args, **kwargs):

        setup = super().setup(request, *args, **kwargs)

        self.user = request.user

        self.context = {
            'redirect': '',
            'title': '',
            'total_title': 'Total', # Total title is dynamic
            'total_groups': 0,
            'num_filtered_groups': 0,
            'groups': [],
            'is_admin': self.user.is_superuser,
            'is_group_coordinator': func.is_approval_group_coordinator(request.user.id),
            'COORDINATOR_ROLE': ApprovalGroupRole.Role.COORDINATOR
        }

        return setup

    def _get_groups(self):
        return ApprovalGroup.objects.none()

    def _append_context(self):
        return {}

    def _apply_baseline_filters(self, request, groups):
        return groups, {}

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        groups = self._get_groups()

        self.context.update(self._append_context())

        # Baseline == active/in_active. can alter the group total
        groups, filter_context = self._apply_baseline_filters(request, groups)
        self.context.update(filter_context)

        total_groups = groups.count()
        self.context['total_groups'] = total_groups

        group_name = request.GET.get('name')
        member_first_name = request.GET.get('member_first_name')
        member_last_name = request.GET.get('member_last_name')

        if group_name:
            groups = groups.filter(name__icontains=group_name)

        if member_first_name or member_last_name:
            filters = Q()
            if member_first_name:
                filters &= Q(roles__user__first_name__icontains=member_first_name)
            if member_last_name:
                filters &= Q(roles__user__last_name__icontains=member_last_name)
            groups = groups.filter(filters).distinct()

        selected_ids = request.GET.getlist('members[]', [])
        coordinator_ids = request.GET.getlist('coordinators[]', [])

        if selected_ids or coordinator_ids:
            groups = func.get_groups_with_matching_composition(
                selected_ids, coordinator_ids, user_groups=groups
            )

        groups = groups.prefetch_related('roles__user')

        groups = groups.annotate(
            is_coordinator=Exists(
                ApprovalGroupRole.objects.filter(
                    user=self.user,
                    role=ApprovalGroupRole.Role.COORDINATOR,
                    group=OuterRef('pk'),
                )
            )
        )

        paginator = Paginator(groups, GROUPS_PER_PAGE)
        num_filtered_groups = paginator.count

        page = request.GET.get('page', 1)
        try:
            groups = paginator.page(page)
        except PageNotAnInteger:
            groups = paginator.page(1)
        except EmptyPage:
            groups = paginator.page(paginator.num_pages)

        self.context['groups'] = groups
        self.context['num_filtered_groups'] = num_filtered_groups

        return render(request, 'key_request/admin/all_groups.html', self.context)

@method_decorator([never_cache, access_admin_only], name='dispatch')
class ViewAllApprovalGroups(ViewApprovalGroups):
    def _get_groups(self):
        return func.get_all_groups()

    def _append_context(self):
        return {
            'title': 'All Approval Groups',
            'redirect': reverse('key_request:all_groups'),
        }

    def _apply_baseline_filters(self, request, groups):
        include_inactive = request.GET.get('include_inactive') == 'true'
        if not include_inactive:
            return groups.filter(is_active=True), {'total_title': 'Total Active'}
        return groups, {}


@method_decorator([never_cache, access_admin_only], name='dispatch')
class CreateApprovalGroup(LoginRequiredMixin, View):

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        return render(request, 'key_request/admin/create_group.html', {
            'form': ApprovalGroupForm(autofill_url=reverse('key_request:user_autofill')),
            'validate_group_url': reverse('key_request:validate_room_group')
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):

        form = ApprovalGroupForm(request.POST)
        if form.is_valid():

            group_name = form.cleaned_data['name']
            group = ApprovalGroup.objects.create(name=group_name)

            member_id_list = form.cleaned_data['member_ids']
            coordinator_id_list = form.cleaned_data['coordinator_ids']
            role_by_id = {
                **{uid: ApprovalGroupRole.Role.MEMBER for uid in member_id_list},
                **{uid: ApprovalGroupRole.Role.COORDINATOR for uid in coordinator_id_list},
            }

            ApprovalGroupRole.objects.bulk_create([
                ApprovalGroupRole(group=group, user_id=user_id, role=role)
                for user_id, role in role_by_id.items()
            ])

            messages.success(request, 'Success! {0} has been created.'.format(group.name))

        else:
            messages.error(request, 'Error! Form is invalid. {0}'.format(appFunc.get_error_messages(form.errors.get_json_data())))

        return HttpResponseRedirect(reverse('key_request:all_groups'))

@method_decorator([never_cache, access_admin_only], name='dispatch')
class EditApprovalGroups(LoginRequiredMixin, View):

    group = None

    def setup(self, request, *args, **kwargs):

        setup = super().setup(request, *args, **kwargs)
        group_id = kwargs.get('group_id')

        self.user = request.user

        self.group = func.get_group_by_id(group_id)

        return setup

    def _make_member_string(self):
        member_ids = func.get_group_member_ids(self.group)
        return ','.join(member_ids)

    def _make_coordinators_string(self):
        member_ids = func.get_group_coordinator_ids(self.group)
        return ','.join(member_ids)

    def _make_member_dict(self):
        return [
            {
                'first_name': user_role.user.first_name,
                'last_name': user_role.user.last_name,
                'id': user_role.user_id,
                'is_coordinator': user_role.role == ApprovalGroupRole.Role.COORDINATOR,
            } for user_role in self.group.roles.all()
        ]


    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        if not self.group:
            messages.error(request, 'Error! No group matches the id specified. It may have been deleted.')
            return HttpResponseRedirect(reverse('key_request:all_groups'))

        return render(request, 'key_request/admin/edit_group.html', {
            'form': ApprovalGroupForm(
                autofill_url=reverse('key_request:user_autofill'),
                initial={
                    'member_ids': self._make_member_string(),
                    'coordinator_ids': self._make_coordinators_string(),
                    'name': self.group.name}
            ),
            'validate_group_url': reverse('key_request:validate_room_group'),
            'group': self.group,
            'group_members': self.group.roles.all().order_by('-role', 'user__first_name', 'user__last_name'),
            'group_members_dict': self._make_member_dict(),
            'COORDINATOR_ROLE': ApprovalGroupRole.Role.COORDINATOR,
        })


    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        form = ApprovalGroupForm(request.POST, instance=self.group)
        if form.is_valid():
            member_id_list = form.cleaned_data['member_ids']
            coordinator_id_list = form.cleaned_data['coordinator_ids']
            role_by_id = {
                **{uid: ApprovalGroupRole.Role.MEMBER for uid in member_id_list},
                **{uid: ApprovalGroupRole.Role.COORDINATOR for uid in coordinator_id_list},
            }
            # Validate ids:
            for uid in member_id_list + coordinator_id_list:
                if not User.objects.filter(id=uid).exists():
                    messages.error(request, 'Error! Invalid user ID: {0}'.format(uid))
                    return HttpResponseRedirect(reverse('key_request:all_groups'))

            ApprovalGroupRole.objects.filter(group=self.group).delete()

            ApprovalGroupRole.objects.bulk_create([
                ApprovalGroupRole(group=self.group, user_id=user_id, role=role)
                for user_id, role in role_by_id.items()
            ])

            group_name = form.cleaned_data['name']

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
    .annotate(
        full_name=Concat('first_name', Value(' '), 'last_name')
    )
    .filter(
        Q(full_name__icontains=name_q)
    ).annotate(
        priority=Case(
            When(full_name__startswith=name_q, then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        )
    )).order_by('priority', 'full_name')
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
@access_group_coordinator_admin_key_request
@require_http_methods(['GET'])
def validate_approval_group(request):
    group_id = request.GET.get('group_id', None)
    selected_name = request.GET.get('name', '').strip()
    selected_ids = request.GET.getlist('members[]', [])
    coordinator_ids = request.GET.getlist('coordinators[]', [])

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

        view_url = reverse('key_request:all_groups') + f"?name={matching_group.name}"
        group_member_names = [user.get_full_name() for user in matching_group.members]

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

    group_matches = func.get_groups_with_matching_composition(selected_ids, coordinator_ids, group_id)

    if group_matches.exists():
        num_matches = group_matches.count()
        q = QueryDict(mutable=True)
        q.setlist('members[]', selected_ids)
        q.setlist('coordinators[]', coordinator_ids)
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
def change_group_activation(request):
    method = request.POST.get('method')
    activation = method == "activate"
    group_id = request.POST.get('group')
    try:
        group = ApprovalGroup.objects.get(id=group_id)
        group_name = group.name

        group.is_active = activation
        group.save()

        if not activation:
            # Remove from all rooms
            group.group_rooms.clear()

        messages.success(request, 'Success! Approval Group {0} has been {1}d.'.format(group_name, method))
    except ApprovalGroup.DoesNotExist:
        messages.error(request, 'Error! Failed to change activation of Approval Group Number {0}.'.format(id))
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
