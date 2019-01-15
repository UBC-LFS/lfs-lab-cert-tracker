from django.conf import settings
from django.contrib.auth.models import User

class SAMLBackend:
    def authenticate(self, request, auth=None):
        user = User.objects.get(username='admin')
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
