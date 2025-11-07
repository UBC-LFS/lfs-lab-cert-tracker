from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views.static import serve
from django.views.decorators.http import require_http_methods
from django.core.exceptions import SuspiciousOperation

from .accesses import access_loggedin_user_pi_admin


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@require_http_methods(['GET'])
def index(request):
    full_name = get_data(request.META, 'full_name')
    last_name = get_data(request.META, 'last_name')
    email = get_data(request.META, 'email')
    username = get_data(request.META, 'username')

    if not request.user or not username:
        raise SuspiciousOperation

    first_name = None
    if full_name:
        first_name = full_name.split(last_name)[0].strip()

    # Update user information if it's None
    update_fields = []
    if not request.user.first_name and first_name:
        request.user.first_name = first_name
        update_fields.append('first_name')
    
    if not request.user.last_name and last_name:
        request.user.last_name = last_name
        update_fields.append('last_name')
        
    if not request.user.email and email:
        request.user.email = email
        update_fields.append('email')
    
    if len(update_fields) > 0:
        request.user.save(update_fields=update_fields)

    return HttpResponseRedirect(reverse('app:my_account', args=[request.user.id]))


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_loggedin_user_pi_admin
@require_http_methods(['POST'])
def read_welcome_message(request, user_id):
    """ Read a welcome message """

    if request.POST.get('read_welcome_message') == 'true':
        request.session['is_first_time'] = False
        return JsonResponse({ 'status': 'success', 'message': 'Success! A user read a welcome message.' })

    return JsonResponse({ 'status': 'error', 'message': 'Error! Something went wrong while reading a welcome message.' })


@login_required(login_url=settings.LOGIN_URL)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@access_loggedin_user_pi_admin
@require_http_methods(['GET'])
def download_user_cert(request, user_id, cert_id, filename):
    path = 'users/{0}/certificates/{1}/{2}'.format(user_id, cert_id, filename)
    return serve(request, path, document_root=settings.MEDIA_ROOT)


# Helper functions

def get_data(meta, field):
    data = settings.SHIB_ATTR_MAP[field]
    if data in meta:
        return meta[data]
    return None
