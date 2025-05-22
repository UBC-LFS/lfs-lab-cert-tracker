from key_request import functions as func

def has_manager_key_requests(request):
    exists = False
    if request.user.is_authenticated:
        exists = func.get_forms_per_manager(request.user).exists()
    return {
        'has_manager_key_requests': exists
    }
