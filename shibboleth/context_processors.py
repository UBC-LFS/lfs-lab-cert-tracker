from django.urls import reverse
from urllib.parse import quote


def login_link(request):
    shib_login = reverse('shibboleth:login')
    full_path = quote(request.get_full_path())
    print('login_link =====', shib_login, full_path, '{0}?target={1}'.format(shib_login, full_path))
    print(request.user, request.user.is_authenticated)
    return { 
        'login_link': '{0}?target={1}'.format(shib_login, full_path)
    }