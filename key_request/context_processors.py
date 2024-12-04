from key_request import functions as func

def has_manager_key_requests(request):
    forms = func.get_forms_per_manager(request.user)
    return {
        'has_manager_key_requests': True if forms.exists() else False
    }
