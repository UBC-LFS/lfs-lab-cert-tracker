from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.urls import reverse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET, require_POST
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.contrib.auth.mixins import LoginRequiredMixin

from app.utils import NUM_PER_PAGE
from .email_coordinator import ApprovalNotificationManager

from .models import Room, RequestForm, RequestFormStatus
from .forms import KeyRequestForm
from . import functions as func
from .dashboard_coordinators import DashboardCoordinator
from .utils import REQUEST_STATUS_DICT

from datetime import date


@method_decorator([never_cache], name='dispatch')
class ManagerDashboard(LoginRequiredMixin, View):

    # Removed setup since no longer doing permission checks
    # def setup(self, request, *args, **kwargs):
    #     setup = super().setup(request, *args, **kwargs)
    #     form_filtered = func.get_forms_per_manager(request.user)
    #     if not form_filtered.exists():
    #         raise PermissionDenied
    #     return setup

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
        form_id = request.POST.get('form')
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
        
        if not form_id or not room_id or (not manager_id and not group_id) or not next:
            raise SuspiciousOperation
        
        request_form_status = RequestFormStatus.objects.create(
            form_id = form_id,
            room_id = room_id,
            manager_id = manager_id,
            group_id = group_id,
            operator_id = request.user.id,
            status = status
        )

        room = Room.objects.filter(id=room_id).first()

        email_manager = ApprovalNotificationManager([request_form_status], status, request.user)
        email_manager.send_email_notification()

        messages.success(request, 'Success! The status of {0} has been updated.'.format(func.display_room(room)))

        return HttpResponseRedirect(next)


@method_decorator([never_cache], name='dispatch')
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

        coordinator = DashboardCoordinator(request.user, query)
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