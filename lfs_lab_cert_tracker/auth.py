from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User

class BackendCWL:
    def authenticate(self, request, token=None):
        # Use the token to authenticate against cwl
        # Check the request and make sure the user is active
        print "HERE"
        print request
        return None

    def get_user(self, user_id):
        # Retrieve the user based on the user_id, pkey of database
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
