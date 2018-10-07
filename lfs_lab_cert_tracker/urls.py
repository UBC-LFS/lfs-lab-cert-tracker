"""lfs_lab_cert_tracker URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.urls import path
from django.contrib import admin

from lfs_lab_cert_tracker import views, api_views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.index),

    path('labs/', views.labs),
    path('certificates/', views.certificates),
    path('users/', views.users),
    path('users/edit_labs', views.edit_user_labs),

    path('users/<int:user_id>/labs/', views.user_labs),
    path('users/<int:user_id>/certificates/', views.user_certificates),

    path('api/labs/', api_views.labs),
    path('api/labs/<int:lab_id>/', api_views.labs),

    path('api/certificates/', api_views.certificates),
    path('api/certificates/<int:cert_id>/', api_views.certificates),

    path('api/labs/<int:lab_id>/certificates/', api_views.lab_certificates),
    path('api/labs/<int:lab_id>/certificates/<int:cert_id>', api_views.lab_certificates),

    url(r'^api/users/<int:user_id>/certificates/', views.user_certificates),
    url(r'^api/users/<int:user_id>/certificates/<int:cert_id>', views.user_certificates),

    url(r'^api/users/<int:user_id>/labs/', views.user_certificates),
    url(r'^api/users/<int:user_id>/labs/<int:lab_id>', views.user_certificates),
]

urlpatterns += [
    url(r'^accounts/', include('django.contrib.auth.urls')),
]
