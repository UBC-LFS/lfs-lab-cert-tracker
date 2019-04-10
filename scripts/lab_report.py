from lfs_lab_cert_tracker.models import Lab, UserLab

import argparse
import datetime
import sys

def run(lab_name):
    try:
        lab = Lab.objects.get(name=lab_name)
        user_labs = UserLab.objects.filter(lab=lab) \
            .prefetch_related('user') \
            .prefetch_related('lab')

        print("lab,cwl,first_name,last_name")
        for ul in user_labs:
            print(ul.lab.name, ul.user.cwl, ul.user.first_name, ul.user.last_name, is_expired)

    except Lab.DoesNotExist:
        print("Lab %s does not exist" % lab_name)
        print("Available labs:")
        for lab in Lab.objects.all():
            print(lab.name)

