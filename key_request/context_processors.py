from app import functions as func

def is_manager(request):
    exists = False
    if request.user.is_authenticated:
        exists = func.is_pi(request.user.id)
    return {
        'has_manager_key_requests': exists
    }
