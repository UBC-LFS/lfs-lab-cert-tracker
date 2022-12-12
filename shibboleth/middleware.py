from django.contrib.auth.middleware import RemoteUserMiddleware


class CustomRemoteUserMiddleware(RemoteUserMiddleware):
    def process_request(self, request):
        print('CustomRemoteUserMiddleware', request.user)
    