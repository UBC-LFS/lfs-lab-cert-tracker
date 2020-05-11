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
from django.conf.urls import url, include, handler403, handler403
from django.urls import path
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from lfs_lab_cert_tracker import views, api_views, saml_views

urlpatterns = [
    path('accounts/login/', views.login),
    path('', views.index, name='index'),

    path('users/', views.users, name='users'),
    path('users/<int:user_id>/', views.user_details, name='user_details'),
    path('users/<int:user_id>/work-area/', views.user_labs),
    path('users/<int:user_id>/training-record/', views.user_certs, name='user_certs'),
    path('users/<int:user_id>/training-record/<int:cert_id>/', views.user_cert_details, name='user_cert_details'),
    path('users/<int:user_id>/report/', views.user_report),
    path('users/report/missing-training/', views.users_in_missing_training_report, name='users_in_missing_training_report'),
    path('users/delete/', views.delete_user, name='delete_user'),
    path('users/switch-admin/', views.switch_admin, name='switch_admin'),
    path('users/switch-inactive/', views.switch_inactive, name='switch_inactive'),

    path('all-areas/', views.labs, name='labs'),
    path('areas/<int:lab_id>/add-users/', views.add_users_to_labs, name='add_users_to_labs'),
    path('areas/<int:lab_id>/', views.lab_details, name='lab_details'),

    path('all-trainings/', views.certs, name='certs'),
    path('all-trainings/<int:cert_id>/edit/', views.edit_cert, name='edit_cert'),
    path('media/users/<int:user_id>/certificates/<int:cert_id>/<str:filename>/', views.download_user_cert),

    path('api/users/<int:user_id>/labs/<int:lab_id>/switch_lab_role/', api_views.switch_lab_role),
    path('api/users/<int:user_id>/labs/<int:lab_id>/delete/', api_views.delete_user_lab),
    path('api/users/<int:user_id>/certificates/', api_views.user_certs),
    path('api/users/<int:user_id>/certificates/<int:cert_id>/delete/', api_views.delete_user_certs),

    path('api/labs/', api_views.labs),
    path('api/labs/<int:lab_id>/delete/', api_views.delete_labs),
    path('api/labs/<int:lab_id>/update/', api_views.update_labs),

    path('api/certificates/', api_views.certs),
    path('api/certificates/<int:cert_id>/delete/', api_views.delete_certs),

    path('api/labs/<int:lab_id>/certificates/', api_views.lab_certs),
    path('api/labs/<int:lab_id>/certificates/<int:cert_id>/delete/', api_views.delete_lab_certs),

    path('saml/', saml_views.saml, name='saml'),
    path('attrs/', saml_views.attrs, name='attrs'),
    path('metadata/', saml_views.metadata, name='metadata'),

    path('error/<str:error_msg>/', views.show_error),

    #path('my_login/', views.my_login, name='my_login'),
    #path('admin/', admin.site.urls),
    #path('accounts/admin/', include('django.contrib.auth.urls')),
]

handler403 = views.permission_denied
handler404 = views.page_not_found
