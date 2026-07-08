from key_request import functions as func

def is_room_manager(request):
    exists = False
    if request.user.is_authenticated:
        exists = func.is_room_approver(request.user.id)
    return {
        'is_room_manager': exists
    }
