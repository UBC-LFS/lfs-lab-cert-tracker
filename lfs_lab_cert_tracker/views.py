from django.shortcuts import render


def landing_page(request):
    return render(request, 'lfs_lab_cert_tracker/landing_page.html')


# Exception handlers

def bad_request(request, exception, template_name='400.html'):
    """ Exception handlder for bad request """
    return render(request, 'lfs_lab_cert_tracker/errors/400.html', context={}, status=400)

def permission_denied(request, exception, template_name="403.html"):
    """ Exception handlder for permission denied """
    return render(request, 'lfs_lab_cert_tracker/errors/403.html', context={}, status=403)

def page_not_found(request, exception, template_name="404.html"):
    """ Exception handlder for page not found """
    return render(request, 'lfs_lab_cert_tracker/errors/404.html', context={}, status=404)

def internal_server_error(request, template_name='500.html'):
    ''' Exception handlder internal server error '''
    return render(request, 'lfs_lab_cert_tracker/errors/500.html', context={}, status=500)
