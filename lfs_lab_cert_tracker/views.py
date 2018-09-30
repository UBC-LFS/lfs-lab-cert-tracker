from django.views.decorators.http import require_http_methods
from django.shortcuts import render

from lfs_lab_cert_tracker import api
from lfs_lab_cert_tracker.forms import LabForm, CertForm

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

