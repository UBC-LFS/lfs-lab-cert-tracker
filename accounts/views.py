from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login as DjangoLogin

from .forms import LocalLoginForm


def local_login(request):
    if request.method == 'POST':
        form = LocalLoginForm(request.POST)
        if form.is_valid():
            user = authenticate(username=request.POST['username'], password=request.POST['password'])

            if user:
                # To check whether users are logged in for the first time or not
                request.session['is_first_time'] = True if user.last_login == None else False

                DjangoLogin(request, user)
                return HttpResponseRedirect(reverse('app:user_details', args=[user.id]))
            else:
                messages.error(request, 'Error! No user found.')
        else:
            messages.error('Error! Form is not valid.')

        redirect('accounts:local_login')

    return render(request, 'accounts/local_login.html', {
        'form': LocalLoginForm()
    })
