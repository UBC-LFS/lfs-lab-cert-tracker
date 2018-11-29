"""lfs_lab_cert_tracker URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home') Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.urls import path
from django.contrib import admin
from django.conf import settings
from lfs_lab_cert_tracker import views, api_views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.index),
    path('labs/', views.labs),
    path('certificates/', views.certs),
    path('users/', views.users),
    path('error/<str:error_msg>', views.show_error),

    path('users/<int:user_id>/labs/', views.user_labs),
    path('users/<int:user_id>/certificates/', views.user_certs),
    path('users/<int:user_id>/certificates/<int:cert_id>/', views.user_cert_details),

    path('labs/<int:lab_id>/', views.lab_details),
    path('users/<int:user_id>/', views.user_details),

    path('api/users/', api_views.users),
    path('api/labs/', api_views.labs),
    path('api/labs/<int:lab_id>/', api_views.labs),
    path('api/labs/<int:lab_id>/delete', api_views.delete_labs),
    path('api/certificates/', api_views.certs),
    path('api/certificates/<int:cert_id>/', api_views.certs),
    path('api/certificates/<int:cert_id>/delete', api_views.delete_certs),
    path('api/labs/<int:lab_id>/certificates/', api_views.lab_certs),
    path('api/labs/<int:lab_id>/users/', api_views.user_labs),
    path('api/labs/<int:lab_id>/certificates/<int:cert_id>', api_views.lab_certs),
    path('api/labs/<int:lab_id>/certificates/<int:cert_id>/delete', api_views.delete_lab_certs),
    path('api/users/<int:user_id>/certificates/', api_views.user_certs),
    path('api/users/<int:user_id>/certificates/<int:cert_id>', api_views.user_certs),
    path('api/users/<int:user_id>/certificates/<int:cert_id>/delete', api_views.delete_user_certs),

    path('api/users/<int:user_id>/labs/<int:lab_id>/delete', api_views.delete_user_lab),
]

urlpatterns += [
    path('accounts/', include('django.contrib.auth.urls')),
]
