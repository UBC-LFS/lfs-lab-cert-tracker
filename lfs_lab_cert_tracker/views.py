from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from lfs_lab_cert_tracker import api

@require_http_methods(['GET', 'POST', 'DELETE'])
def certificates(request, cert_id=None):
    if request.method == 'GET':
        res = api.get_certs()
        return JsonResponse(res)
    elif request.method == 'POST':
        data = request.data
        res = api.create_cert(data['name'])
        return JsonResponse(res)
    elif request.method == 'DELETE':
        res = api.delete_cert(cert_id)
        return JsonResponse(res)

@require_http_methods(['GET', 'POST', 'DELETE'])
def labs(request, lab_id=None):
    if request.method == 'GET':
        res = api.get_labs()
        return JsonResponse(res)
    elif request.method == 'POST':
        data = request.data
        res = api.create_lab(data['name'])
        return JsonResponse(res)
    elif request.method == 'DELETE':
        res = api.delete_lab(lab_id)
        return JsonResponse(res)

@require_http_methods(['GET', 'POST', 'DELETE'])
def lab_certificates(request, cert_id=None):
    if request.method == 'GET':
        res = api.get_lab_certs(lab_id)
        return JsonResponse(res)
    elif request.method == 'POST':
        res = api.create_lab_cert(lab_id, cert_id)
        return JsonResponse(res)
    elif request.method == 'DELETE':
        res = api.delete_lab_cert(lab_id, cert_id)
        return JsonResponse(res)
