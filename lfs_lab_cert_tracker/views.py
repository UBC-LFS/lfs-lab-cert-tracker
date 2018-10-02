from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render

from lfs_lab_cert_tracker import api
from lfs_lab_cert_tracker.forms import LabForm, CertForm

@login_required
@require_http_methods(['GET'])
def index(request):
    return render(request, 'lfs_lab_cert_tracker/index.html')

@login_required
@require_http_methods(['GET'])
def labs(request):
    labs = api.get_labs()
    return render(request,
        'lfs_lab_cert_tracker/labs.html',
        {
            'lab_list': labs,
            'lab_form': LabForm(),
        }
    )

@login_required
@require_http_methods(['GET'])
def certificates(request):
    certs = api.get_certs()
    return render(request,
            'lfs_lab_cert_tracker/certs.html',
            {
                'cert_list': certs,
                'cert_form': CertForm(),
            }
    )

