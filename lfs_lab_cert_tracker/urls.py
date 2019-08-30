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

    path('users/', views.users),
    path('users/<int:user_id>/', views.user_details),
    path('users/<int:user_id>/labs/', views.user_labs),
    path('users/<int:user_id>/certificates/', views.user_certs, name='user_certs'),
    path('users/<int:user_id>/certificates/<int:cert_id>/', views.user_cert_details, name='user_cert_details'),
    path('users/<int:user_id>/report/', views.user_report),

    path('labs/', views.labs, name='labs'),
    path('labs/<int:lab_id>/', views.lab_details),

    path('certificates/', views.certs),
    path('media/users/<int:user_id>/certificates/<int:cert_id>/<str:filename>', views.download_user_cert),

    path('api/users/', api_views.users),
    path('api/users/<int:user_id>/delete', api_views.delete_user),
    path('api/users/<int:user_id>/switch_admin', api_views.switch_admin),
    path('api/users/<int:user_id>/switch_inactive', api_views.switch_inactive),
    path('api/users/<int:user_id>/labs/<int:lab_id>/switch_lab_role', api_views.switch_lab_role),
    path('api/users/<int:user_id>/labs/<int:lab_id>/delete', api_views.delete_user_lab),
    path('api/users/<int:user_id>/certificates/', api_views.user_certs),
    path('api/users/<int:user_id>/certificates/<int:cert_id>/delete', api_views.delete_user_certs),

    path('api/labs/', api_views.labs),
    path('api/labs/<int:lab_id>/users/', api_views.user_labs),
    path('api/labs/<int:lab_id>/delete', api_views.delete_labs),
    path('api/labs/<int:lab_id>/update', api_views.update_labs),

    path('api/certificates/', api_views.certs),
    path('api/certificates/<int:cert_id>/delete', api_views.delete_certs),

    path('api/labs/<int:lab_id>/certificates/', api_views.lab_certs),
    path('api/labs/<int:lab_id>/certificates/<int:cert_id>/delete', api_views.delete_lab_certs),

    path('saml/', saml_views.saml, name='saml'),
    path('attrs/', saml_views.attrs, name='attrs'),
    path('metadata/', saml_views.metadata, name='metadata'),

    path('error/<str:error_msg>', views.show_error),


    # -------- to be removed --------- #
    path('my_login/', views.my_login, name='my_login'),
    path('accounts/admin/', include('django.contrib.auth.urls')),
    #path('admin/', admin.site.urls)
]

handler403 = views.permission_denied
handler404 = views.page_not_found
