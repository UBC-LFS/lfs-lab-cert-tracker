from key_request import functions as func

def has_manager_key_requests(request):
    requests, new_requests = func.get_manager_dashboard(request.user)
    return {
        'has_manager_key_requests': True if len(requests) > 0 else False
    }
