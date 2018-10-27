from lfs_lab_cert_tracker.models import UserLab

def is_admin(user):
    return user.groups.filter(name='admin').exists()

def is_principal_investigator(user_id, lab_id):
    user_lab = UserLab.objects.get(user=user_id, lab=lab_id)
    return user_lab.role == UserLab.PRINCIPAL_INVESTIGATOR
