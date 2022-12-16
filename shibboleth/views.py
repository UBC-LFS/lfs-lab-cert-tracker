from django.conf import settings
from django.views import View
from django.shortcuts import render, redirect
from urllib.parse import quote


class Shib_Login(View):
    redirect_field_name = 'target'

    def get(self, request, *args, **kwargs):
        target = request.GET.get(self.redirect_field_name, '')
        login = settings.LOGIN_URL + '?target={0}'.format(quote(target))

        print('Shib_Login =====', login)
        print(request.user, request.user.is_authenticated)
        return redirect(login)
