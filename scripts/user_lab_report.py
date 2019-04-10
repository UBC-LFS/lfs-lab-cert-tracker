from lfs_lab_cert_tracker.models import User, Lab, UserLab
from lfs_lab_cert_tracker import api

import argparse
import datetime
import sys

def run(cwl, lab_name):
    try:
        user = User.objects.get(cwl=cwl)
        lab = Lab.objects.get(name=lab_name)
        user_lab = UserLab.objects.get(user=user, lab=lab)
        missing_user_lab_certs = api.get_missing_lab_certs(user, lab)

        if not missing_user_lab_certs:
            print("User %s fufills requirements for %s" % (user.cwl, lab.name))
            return

        print("User %s is missing ..." % user.cwl)
        for mc in missing_user_lab_certs:
            print(mc['name'])

    except (User.DoesNotExist):
        print("User %s does not exist" % cwl)
        print("Available labs:")
        for user in User.objects.all():
            print(user.cwl)
    except (Lab.DoesNotExist):
        print("Lab %s does not exist" % lab_name)
        print("Available labs:")
        for lab in Lab.objects.all():
            print(lab.name)
    except (UserLab.DoesNotExist):
        print("User %s is not registered in %s" % (cwl, lab_name))

