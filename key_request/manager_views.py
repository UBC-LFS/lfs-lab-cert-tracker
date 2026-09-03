from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.cache import never_cache, cache_control
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.urls import reverse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.contrib.auth.mixins import LoginRequiredMixin
from psycopg2 import IntegrityError

from app.accesses import access_group_coordinator_admin_key_request, access_pi_admin_key_request
from app.utils import NUM_PER_PAGE
from lfs_lab_cert_tracker import settings
from .admin_views import ViewApprovalGroups
from .email_coordinator import ApprovalNotificationManager

from .models import Room, RequestForm, RequestFormStatus, ApprovalGroupRole, ApprovalGroup
from .forms import KeyRequestForm, ApprovalGroupForm, UserApprovalGroupForm
from . import functions as func
from .dashboard_coordinators import DashboardCoordinator, GroupFormProcessor, ManagerFormProcessor
from .utils import REQUEST_STATUS_DICT

import json
from datetime import date


@method_decorator([never_cache, access_pi_admin_key_request], name='dispatch')
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

        # NOTE: there is one form PER group and one form PER manager
        coordinator = DashboardCoordinator(request.user, query)
        coordinator.run()

        page = request.GET.get('page', 1)
        paginator = Paginator(coordinator.get_forms(), NUM_PER_PAGE)

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
            'total_forms': coordinator.get_total_forms(),
            'num_new_forms': coordinator.get_num_new_forms(),
            'num_filtered_forms': coordinator.get_num_filtered_forms(),
            'forms': forms,
            'post_url': reverse('key_request:manager_dashboard'),
            'req_status_dict': REQUEST_STATUS_DICT,
            'search_filter_options': func.search_filter_options,
            'is_admin': True if request.user.is_superuser else False
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        next_url = request.POST.get('next')
        if not next_url:
            raise SuspiciousOperation

        request_form_identifier = request.POST.get('request_form_identifier')

        try:
            identifier = json.loads(request_form_identifier)
        except (TypeError, json.JSONDecodeError):
            messages.error(request, 'Error: Invalid request_form_identifier.')
            return HttpResponseRedirect(next_url)

        status = request.POST.get('status')

        if not status:
            messages.error(request, 'Error: A status must be selected.')
            return HttpResponseRedirect(next_url)
        
        rfs = func.create_and_process_request_form_identifier(identifier, request.user, status)

        if not rfs:
            messages.error(request, 'Error: Could not find the request form specified.')
            return HttpResponseRedirect(next_url)

        rfs.save()
        room_id = identifier.get('room_id')
        room = Room.objects.filter(id=room_id).first()

        email_manager = ApprovalNotificationManager([rfs], status, request.user)
        email_manager.send_email_notification()

        messages.success(request, 'Success! The status of {0} has been updated.'.format(func.display_room(room)))

        return HttpResponseRedirect(next_url)


@method_decorator([never_cache, access_pi_admin_key_request], name='dispatch')
class UpdateExpiryDate(LoginRequiredMixin, View):

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        form_id = request.POST.get('form', None)
        expiry_date = request.POST.get('expiry_date', None)
        next = request.POST.get('next', None)

        if not form_id or not next:
            raise SuspiciousOperation

        if not expiry_date:
            messages.error(request, 'An error occurred. <strong>Expiry Date:</strong> This field is required.')
            return HttpResponseRedirect(next)

        duration = func.convert_str_to_date(expiry_date) - date.today()
        if duration.days < 0:
            messages.error(request, 'An error occurred. Please enter a valid <strong>Expiry Date</strong>.')
            return HttpResponseRedirect(next)

        RequestForm.objects.filter(id=form_id).update(expiry_date=expiry_date)
        messages.success(request, 'Success! <strong>Expiry Date</strong> has been updated.')
        return HttpResponseRedirect(next)


@method_decorator([never_cache, access_pi_admin_key_request], name='dispatch')
class ManagerRooms(LoginRequiredMixin, View):

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        query = {
            'building': request.GET.get('building'),
            'floor': request.GET.get('floor'),
            'number': request.GET.get('number'),
            'name': request.GET.get('name')
        }

        # Need to exclude the request supervisor from the list of rooms because they are not a manager of the room
        coordinator = DashboardCoordinator(request.user, query, [ManagerFormProcessor, GroupFormProcessor])
        room_list = coordinator.get_all_rooms()
        total = len(room_list)

        filtered_room_list = coordinator.get_all_filtered_rooms()
        num_filtered_rooms = len(filtered_room_list)

        page = request.GET.get('page', 1)
        paginator = Paginator(filtered_room_list, NUM_PER_PAGE)

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
            'search_filter_options': func.search_filter_options,
            'is_admin': True if request.user.is_superuser else False
        })

@method_decorator([never_cache, access_pi_admin_key_request], name='dispatch')
class ViewManagerApprovalGroups(ViewApprovalGroups):

    def _append_context(self):
        return {
            'title': 'My Approval Groups',
            'redirect': reverse('key_request:manager_groups'),
        }

    def _get_groups(self):
       return func.get_all_active_user_groups(self.user)

@method_decorator([never_cache, access_group_coordinator_admin_key_request], name='dispatch')
class EditManagerGroups(LoginRequiredMixin, View):

    group = None

    def setup(self, request, *args, **kwargs):

        setup = super().setup(request, *args, **kwargs)
        group_id = kwargs.get('group_id')

        self.user = request.user

        self.group = func.get_group_by_id(group_id)

        return setup


    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):

        if not self.group:
            messages.error(request, 'Error! No group matches the id specified. It may have been deleted.')
            return HttpResponseRedirect(reverse('key_request:all_groups'))

        members = []
        for member in self.group.roles.all():
            if member.user == self.user:
                members.insert(0, member)
            else:
                members.append(member)


        return render(request, 'key_request/manager_dashboard/edit_group_as_manager.html', {
            'form': UserApprovalGroupForm(initial={
                'group': self.group
            }),
            'group': self.group,
            'members': members,
            'user': self.user,
            'role_choices': ApprovalGroupRole.Role.choices
        })

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        username = request.POST.get('user')

        user = User.objects.filter(username=username)
        if not user.exists():
            messages.error(request, 'Error! Could not find user with CWL {0}.'.format(username))
            return HttpResponseRedirect(reverse('key_request:manager_edit_group', kwargs={'group_id': self.group.id}))
        user = user.first()

        if user == request.user:
            messages.warning(request, 'Cannot update self. Please contact admin.')
            return HttpResponseRedirect(reverse('key_request:manager_edit_group', kwargs={'group_id': self.group.id}))

        role_id = request.POST.get('role')
        try:
            # NOTE: exclude role from lookup & keep in defaults
            role, created = ApprovalGroupRole.objects.get_or_create(
                group=self.group,
                user_id=user.id
            )


            if not created:

                msg = 'Warning! User {0} is already in the group.'.format(user.get_full_name())
                if role.role != role_id:
                    role.role = role_id
                    role.save()
                    role_str = func.get_approval_role_string(role_id)

                    msg += f' Role has been updated to {role_str}.'
                messages.warning(request, msg)
            else:
                messages.success(request, 'Success! User {0} has been added to the group.'.format(user.get_full_name()))
        except IntegrityError:
            messages.error(request, 'Error! Failed to add User {0}. They may already exist within the group.').format(user.get_full_name())

        return HttpResponseRedirect(reverse('key_request:manager_edit_group', kwargs={'group_id': self.group.id}))


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_group_coordinator_admin_key_request
@require_http_methods(['POST'])
def delete_group_member(request, group_id):
    user_id = request.POST.get('user')
    try:
        member = ApprovalGroupRole.objects.filter(group_id=group_id, user_id=user_id).first()
        name = member.user.get_full_name()
        member.delete()
        messages.success(request, 'Success! User {0} has been removed from the group.'.format(name))
    except (ApprovalGroupRole.DoesNotExist, User.DoesNotExist):
        messages.error(request, 'Error! Failed to remove the User. They may have already been removed.')
    return redirect(reverse('key_request:manager_edit_group', kwargs={'group_id': group_id}))


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_group_coordinator_admin_key_request
@require_http_methods(['POST'])
def change_group_member_role(request, group_id):
    user_id = request.POST.get('user')
    role_id = request.POST.get('role')

    try:
        member = ApprovalGroupRole.objects.filter(group_id=group_id, user_id=user_id).first()
        name = member.user.get_full_name()
        member.role = int(role_id)
        member.save()
        role_string = member.get_role_display()
        messages.success(request, 'Success! User {0}\'s role has been updated to {1}.'.format(name, role_string))
    except ApprovalGroupRole.DoesNotExist:
        messages.error(request, 'Error! Failed to change the User\'s Role.')
    return redirect(reverse('key_request:manager_edit_group', kwargs={'group_id': group_id}))
