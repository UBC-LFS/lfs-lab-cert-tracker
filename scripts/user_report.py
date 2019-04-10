from lfs_lab_cert_tracker.models import User
from lfs_lab_cert_tracker import api

import argparse
import datetime
import sys

def run(cwl):
    try:
        user = User.objects.get(cwl=cwl)
        user_certs = api.get_user_certs(user)
        missing_certs = api.get_missing_certs(user)
        expired_certs = api.get_expired_certs(user)

        print("User %s" % user.cwl)
        print("Has Certs...")
        for uc in user_certs:
            print(uc['name'])

        print("")

        print("Has Expired Certs")
        for ec in expired_certs:
            print(ec['name'])

        print("")

        print("Is Missing Certs")
        for mc in missing_certs:
            print(mc['name'])

        print("")

    except (User.DoesNotExist):
        print("User %s does not exist" % cwl)
        print("Available users:")
        for user in User.objects.all():
            print(user.cwl)

