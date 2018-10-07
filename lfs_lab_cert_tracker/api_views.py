from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from lfs_lab_cert_tracker import api

@login_required
@require_http_methods(['GET', 'POST', 'DELETE'])
def certificates(request, cert_id=None):
    user = request.user
    if request.method == 'GET':
        res = api.get_certs()
        return JsonResponse(res, safe=False)
    elif request.method == 'POST' and user.has_perm('lfs_lab_cert_tracker.add_cert'):
        data = request.POST
        res = api.create_cert(data['name'])
        return JsonResponse(res)
    elif request.method == 'DELETE' and user.has_perm('lfs_lab_cert_tracker.delete_cert'):
        res = api.delete_cert(cert_id)
        return JsonResponse(res)

@login_required
@require_http_methods(['GET', 'POST', 'DELETE'])
def labs(request, lab_id=None):
    user = request.user
    if request.method == 'GET':
        res = api.get_labs()
        return JsonResponse(res, safe=False)
    elif request.method == 'POST' and user.has_perm('lfs_lab_cert_tracker.add_lab'):
        data = request.POST
        res = api.create_lab(data['name'])
        return JsonResponse(res)
    elif request.method == 'DELETE' and user.has_perm('lfs_lab_cert_tracker.delete_lab'):
        res = api.delete_lab(lab_id)
        return JsonResponse(res)

@login_required
@require_http_methods(['GET', 'POST', 'DELETE'])
def lab_certificates(request, lab_id=None, cert_id=None):
    if request.method == 'GET':
        res = api.get_lab_certs(lab_id)
        return JsonResponse(res, safe=False)
    elif request.method == 'POST':
        data = request.POST
        res = api.create_lab_cert(data['lab_id'], data['cert_id'])
        return JsonResponse(res)
    elif request.method == 'DELETE':
        data = request.POST
        res = api.delete_lab_cert(data['lab_id'], data['cert_id'])
        return JsonResponse(res)

@login_required
@require_http_methods(['GET', 'POST', 'DELETE'])
def user_certificates(request, user_id=None, cert_id=None): 
    if request.method == 'GET':
        res = api.get_user_certs(user_id)
        return JsonResponse(res, safe=False)
    elif request.method == 'POST':
        data = request.POST
        res = api.ceate_user_cert(data['user_id'], data['cert_id'])
        return JsonResponse(res)
    elif request.method == 'DELETE':
        data = request.POST
        res = api.delete_user_cert(data['user_id'], data['cert_id'])
        return JsonResponse(res)

@login_required
@require_http_methods(['GET', 'POST', 'DELETE'])
def user_labs(request, user_id=None, lab_id=None): 
    if request.method == 'GET':
        res = api.get_user_labs(user_id)
        return JsonResponse(res, safe=False)
    elif request.method == 'POST':
        data = request.POST
        res = api.ceate_user_lab(data['user_id'], data['lab_id'])
        return JsonResponse(res)
    elif request.method == 'DELETE':
        data = request.POST
        res = api.delete_user_lab(data['user_id'], data['lab_id'])
        return JsonResponse(res)
