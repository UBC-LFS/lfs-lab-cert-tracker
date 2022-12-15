from django.urls import reverse
from urllib.parse import quote


def login_target(request):
    
    print('login target', request.user, request.user.is_authenticated)

    full_path = quote(request.get_full_path())
    login = 'login'
    ll = '{0}?target={1}'.format(login, full_path)

    print(full_path, ll)

    return { 
        'login_link': ll 
    }
