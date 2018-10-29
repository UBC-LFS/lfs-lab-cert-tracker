from lfs_lab_cert_tracker.models import UserLab

def is_admin(user):
    return user.groups.filter(name='admin').exists()

def is_principal_investigator(user_id, lab_id):
    return UserLab.objects.filter(user=user_id, lab=lab_id, role=UserLab.PRINCIPAL_INVESTIGATOR).exists()
