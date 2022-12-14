def authenticate_user(request):
    user_auth = None
    print(request.user, request.user.is_authenticated)
    
    return {
        'user_auth': user_auth
    }
