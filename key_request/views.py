from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET
from django.contrib.auth.mixins import LoginRequiredMixin

from app.utils import NUM_PER_PAGE
from .dashboard_coordinators import ApplicantRequestFormProcessor

from .utils import APPROVED
from . import functions as func


@method_decorator([never_cache], name='dispatch')
class Index(LoginRequiredMixin, View):

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        form_list = request.user.request_forms.all()

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

        processor = ApplicantRequestFormProcessor(request.user)
        forms = processor.get_all_status_annotated_forms(forms)


        for form in forms:
            room_ids = form.rooms.all().values_list('id', flat=True)
            user_trainings, total_missing, total_expired = func.check_user_trainings(form.user, room_ids)
            form.user_trainings = user_trainings
            form.total_missing = total_missing
            form.total_expired = total_expired

        return render(request, 'key_request/index.html', {
            'total_forms': len(form_list),
            'forms': forms,
            'is_admin': True if request.user.is_superuser else False
        })