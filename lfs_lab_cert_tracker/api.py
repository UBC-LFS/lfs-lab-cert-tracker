from datetime import datetime
from django.shortcuts import get_object_or_404
from django.forms.models import model_to_dict
from django.http import Http404

from django.contrib.auth.models import User as AuthUser
from .models import UserCert, LabCert, UserLab, Cert, Lab


def add_missing_certs(users):
    """ Add missing certs into users """
    for user in users:
        certs = get_missing_certs_query_object(user.id)
        if len(certs) > 0:
            user.missing_certs = certs
        else:
            user.missing_certs = None
    return users


def get_missing_certs(user_id):
    # Get the labs that the user is signed up for
    user_lab_ids = UserLab.objects.filter(user_id=user_id).values_list('lab_id')
    lab_certs = LabCert.objects.filter(lab_id__in=user_lab_ids).distinct('cert').prefetch_related('cert')

    # From these labs determine which certs are missing or expired
    user_cert_ids = UserCert.objects.filter(user_id=user_id).values_list('cert_id')
    missing_user_certs = lab_certs.exclude(cert_id__in=user_cert_ids)

    return [model_to_dict(missing_user_cert.cert) for missing_user_cert in missing_user_certs]


def is_user_cert_expired(cert):
    now = datetime.now().date()
    return cert.expiry_date is not None and now > cert.expiry_date and cert.expiry_date != cert.completion_date


def get_expired_certs(user_id):
    user_certs = UserCert.objects.filter(user_id=user_id).prefetch_related('cert')
    expired_user_certs = []
    now = datetime.now()
    for uc in user_certs:
        if is_user_cert_expired(uc):
            expired_user_certs.append(uc)
    return [model_to_dict(uc.cert) for uc in expired_user_certs]


def get_user_labs(user_id, is_principal_investigator=None):
    if is_principal_investigator:
        user_labs = UserLab.objects.filter(user=user_id, role=UserLab.PRINCIPAL_INVESTIGATOR)
    else:
        user_labs = UserLab.objects.filter(user=user_id)
    return [model_to_dict(user_lab.lab) for user_lab in user_labs]


def get_user_certs_404(user_id):
    """ Get all certs of an user """
    user = get_user_404(user_id)
    return user.usercert_set.all()


def get_cert(cert_id):
    """ Find a certificate by id """

    try:
        cert = Cert.objects.get(id=cert_id)
        return model_to_dict(cert)
    except Cert.DoesNotExist:
        return None


def get_user_cert_404(user_id, cert_id):
    """ Get a cert of an user """
    user = get_user_404(user_id)
    uc = user.usercert_set.filter(cert_id=cert_id)
    if uc.exists():
        return uc.first()
    raise Http404


def get_missing_certs_query_object(user_id):
    user_lab_ids = UserLab.objects.filter(user_id=user_id).values_list('lab_id')
    lab_certs = LabCert.objects.filter(lab_id__in=user_lab_ids).distinct('cert').prefetch_related('cert')

    # From these labs determine which certs are missing or expired
    user_cert_ids = UserCert.objects.filter(user_id=user_id).values_list('cert_id')

    return lab_certs.exclude(cert_id__in=user_cert_ids)


def update_or_create_user_cert(user_id, cert_id, cert_file, completion_date, expiry_date):
    user_cert, created = UserCert.objects.get_or_create(
        user_id=user_id,
        cert_id=cert_id,
        defaults={
            'cert_file': cert_file,
            'uploaded_date': datetime.now(),
            'completion_date': completion_date,
            'expiry_date': expiry_date
        }
    )
    if not created:
        user_cert.cert_file = cert_file
        user_cert.uploaded_date = datetime.now()
        user_cert.completion_date = completion_date
        user_cert.expiry_date = expiry_date
        user_cert.save()

    return model_to_dict(user_cert)


def get_users_missing_certs(lab_id):
    """
    Given a lab returns users that are missing certs and the certs they are missing
    """
    lab_users = UserLab.objects.filter(lab=lab_id).prefetch_related('user')

    users_missing_certs = []
    for lab_user in lab_users:
        missing_lab_certs = get_missing_lab_certs(lab_user.user_id, lab_id)
        if missing_lab_certs:
            users_missing_certs.append((lab_user, missing_lab_certs))

    return [(model_to_dict(user_missing_certs.user), missing_lab_cert) for user_missing_certs, missing_lab_cert in users_missing_certs]


def get_users_expired_certs(lab_id):
    lab_users = UserLab.objects.filter(lab=lab_id).prefetch_related('user')

    users_expired_certs = []
    for lab_user in lab_users:
        user_certs = UserCert.objects.filter(user=lab_user.user_id).prefetch_related('cert')
        required_certs = LabCert.objects.filter(lab=lab_id).prefetch_related('cert')

        user_cert_ids = set(user_certs.values_list('cert_id', flat=True))
        required_cert_ids = set(required_certs.values_list('cert_id', flat=True))

        expired_certs = []
        for uc in user_certs:
            if uc.cert.id in required_cert_ids and is_user_cert_expired(uc):
                expired_certs.append(uc.cert)

        if len(expired_certs) > 0:
            users_expired_certs.append({
                'user': lab_user.user,
                'expired_certs': expired_certs
            })

    return users_expired_certs


def get_missing_lab_certs(user_id, lab_id):
    user_certs = UserCert.objects.filter(user=user_id).prefetch_related('cert')
    required_certs = LabCert.objects.filter(lab=lab_id).prefetch_related('cert')

    user_cert_ids = set(user_certs.values_list('cert_id', flat=True))
    required_cert_ids = set(required_certs.values_list('cert_id', flat=True))

    missing = []
    for rc in required_certs:
        if rc.cert.id not in user_cert_ids:
            missing.append(rc.cert)

    #for uc in user_certs:
    #    if uc.cert.id in required_cert_ids and is_user_cert_expired(uc):
    #        expiried.append(uc.cert)

    return [model_to_dict(m) for m in missing]


def get_user_certs(user_id):
    user_certs = UserCert.objects.filter(user_id=user_id).prefetch_related('cert')
    res = []
    for user_cert in user_certs:
        dict_user_cert = model_to_dict(user_cert)
        dict_user_cert.update(model_to_dict(user_cert.cert))
        res.append(dict_user_cert)
    return res


def get_lab_certs(lab_id, n=None):
    """ Get all certificates in a lab """

    lab_certs = LabCert.objects.filter(lab=lab_id).prefetch_related('cert')
    return [model_to_dict(lab_cert.cert) for lab_cert in lab_certs]


def get_user_404(user_id):
    """ Get an user or 404 """
    return get_object_or_404(AuthUser, id=user_id)


def get_area_404(area_id):
    """ Get an user or 404 """
    return get_object_or_404(Lab, id=area_id)


# Helper methods

def validate_parameters(request, params):
    """ Validate request parameters """
    for param in params:
        if request.GET.get(param) is None: raise Http404
    return True


def validate_url_tab(request, path):
    """ Validate a tab name in url """
    if request.GET.get('t') not in path:
        raise Http404


def can_req_parameters_access(request, params):
    """ Check whether request parameters are valid or not """
    if validate_parameters(request, params):
        validate_url_tab(request, ['all', 'report', 'new'])
