from key_request import functions as func


# TODO: Change to is_room_approver then update template to use is_room_approver instead of is_room_manager & update settings.py
# TODO: remove is_request_supervisor and update settings.py
def is_room_manager(request):
    exists = False
    if request.user.is_authenticated:
        exists = func.is_room_approver(request.user.id)
    return {
        'is_room_manager': exists
    }

def is_request_supervisor(request):
    exists = False
    if request.user.is_authenticated:
        exists = func.is_request_supervisor(request.user.id)

    return {
        'is_request_supervisor': exists
    }
