from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as DjangoLogin

from .forms import LocalLoginForm


def login(request):
    print('login', hasattr(request, 'user'), request.user)
    return render(request, 'accounts/meta.html', {
        'meta': request.META
    })


def local_login(request):
    ''' local login '''

    if request.method == 'POST':
        form = LocalLoginForm(request.POST)
        if form.is_valid():
            user = authenticate(username=request.POST['username'], password=request.POST['password'])
            if user is not None:

                # To check whether users are logged in for the first time or not
                request.session['is_first_time'] = True if user.last_login == None else False

                DjangoLogin(request, user)
                return redirect('index')
            else:
                messages.error(request, 'Error! User not found.')
                return redirect('local_login')
        else:
            errors = form.errors.get_json_data()
            messages.error(request, 'Error! Please check your CWL or password. {0}'.format( uApi.get_error_messages(errors) ))
            return redirect('local_login')

    return render(request, 'accounts/local_login.html', { 
        'form': LocalLoginForm() 
    })
