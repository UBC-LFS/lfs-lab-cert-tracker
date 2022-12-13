from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.middleware import RemoteUserMiddleware
from django.core.exceptions import ImproperlyConfigured


# Reference
# https://github.com/django/django/blob/main/django/contrib/auth/middleware.py


class CustomRemoteUserMiddleware(RemoteUserMiddleware):
    '''
    Custom Remote User Middleware
    '''

    header = settings.SHIBBOLETH_ATTRIBUTES['header']
    full_name = settings.SHIBBOLETH_ATTRIBUTES['full_name']
    last_name = settings.SHIBBOLETH_ATTRIBUTES['last_name']
    email = settings.SHIBBOLETH_ATTRIBUTES['email']

    force_logout_if_no_header = True

    def process_request(self, request):
        # AuthenticationMiddleware is required so that request.user exists.
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                'The Django remote user auth middleware requires the'
                ' authentication middleware to be installed.  Edit your'
                ' MIDDLEWARE setting to insert'
                ' "django.contrib.auth.middleware.AuthenticationMiddleware"'
                ' before the RemoteUserMiddleware class.'
            )
        try:
            username = request.META[self.header]
        except KeyError:
            # If specified header doesn't exist then remove any existing
            # authenticated remote-user, or return (leaving request.user set to
            # AnonymousUser by the AuthenticationMiddleware).
            if self.force_logout_if_no_header and request.user.is_authenticated:
                self._remove_invalid_user(request)
            return
        # If the user is already authenticated and that user is the user we are
        # getting passed in the headers, then the correct user is already
        # persisted in the session and we don't need to continue.
        if request.user.is_authenticated:
            if request.user.get_username() == self.clean_username(username, request):
                return
            else:
                # An authenticated user is associated with the request, but
                # it does not match the authorized user in the header.
                self._remove_invalid_user(request)

        # We are seeing this user for the first time in this session, attempt
        # to authenticate the user.
        user = authenticate(request, remote_user=username)
        if user:
            # User is valid.  Set request.user and persist user in the session
            # by logging the user in.
            request.user = user
            login(request, user)

            # Check whether first name, last name and email are stored in the database or not
            full_name = request.META[self.full_name]
            last_name = request.META[self.last_name]
            email = request.META[self.email]
            first_name = full_name.split(last_name)[0]

            update_fields = []
            if not user.first_name:
                user.first_name = first_name.strip()
                update_fields.append('first_name')
            
            if not user.last_name:
                user.last_name = last_name
                update_fields.append('last_name')
            
            if not user.email:
                user.email = email
                update_fields.append('email')

            if len(update_fields) > 0:
                user.save(update_fields=update_fields)


            
    