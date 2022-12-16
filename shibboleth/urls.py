from django.urls import path

from . import views

app_name = 'shibboleth'

urlpatterns = [
    path('login/', views.Shib_Login.as_view(), name='login')
]
