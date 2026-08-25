from django.utils.decorators import method_decorator
from django.urls import reverse
from django.views.decorators.cache import cache_control, never_cache

from app.accesses import access_supervisor_admin_request

from key_request.dashboard_coordinators import SupervisorRequestFormProcessor
from .admin_views import ViewFormDetails, RequestView


@method_decorator([never_cache, access_supervisor_admin_request], name='dispatch')
class SupervisorRequests(RequestView):
    processor_classes = [SupervisorRequestFormProcessor]
    template_name = 'key_request/supervisor/supervisor_dashboard.html'
    title = 'Supervisor Dashboard'
    details_url_name = 'key_request:supervisor_form_details'


@method_decorator([never_cache, access_supervisor_admin_request], name='dispatch')
class SupervisorRequestDetails(ViewFormDetails):
    back_label = 'Supervisor Dashboard'
    show_email_tab = False

    def setup(self, request, *args, **kwargs):
        setup = super().setup(request, *args, **kwargs)
        form_id = kwargs.get('form_id')
        self.url = reverse('key_request:supervisor_form_details', args=[form_id])

        return setup