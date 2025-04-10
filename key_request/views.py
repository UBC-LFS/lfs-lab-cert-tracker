from django.views.decorators.cache import  never_cache
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET
from django.contrib.auth.mixins import LoginRequiredMixin

from app.utils import NUM_PER_PAGE

from . import functions as func
from .forms import APPROVED


@method_decorator([never_cache], name='dispatch')
class Index(LoginRequiredMixin, View):

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        form_list = request.user.requestform_set.all()

        for i, form in enumerate(form_list):
            form.counter = len(form_list) - i

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