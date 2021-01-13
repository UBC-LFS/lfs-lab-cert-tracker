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



    # Users - classes

    path('users/report/missing-trainings/', views.UserReportMissingTrainingsView.as_view(), name='user_report_missing_trainings'),
    path('users/new/', views.NewUserView.as_view(), name='new_user'),
    path('users/all/', views.AllUsersView.as_view(), name='all_users'),
    path('users/<int:user_id>/', views.UserDetailsView.as_view(), name='user_details'),


    # Users - functions

    path('users/<int:user_id>/report/', views.user_report),
    path('users/report/missing-trainings/download/', views.download_user_report_missing_trainings, name='download_user_report_missing_trainings'),

    # Users - api

    path('api/user/delete/', views.delete_user, name='delete_user'),
    path('api/user/switch-admin/', views.switch_admin, name='switch_admin'),
    path('api/user/switch-inactive/', views.switch_inactive, name='switch_inactive'),
    path('api/users/assign/areas/', views.assign_user_areas, name='assign_user_areas'),



    # Areas - classes

    path('areas/all/', views.AllAreasView.as_view(), name='all_areas'),
    path('areas/<int:area_id>/', views.AreaDetailsView.as_view(), name='area_details'),
    path('users/<int:user_id>/work-area/', views.UserAreasView.as_view(), name='user_areas'),

    # Areas - functions


    # Areas - api

    path('api/area/update/', views.update_area, name='update_area'),
    path('api/area/delete/', views.delete_area, name='delete_area'),
    path('api/area/user/add/', views.add_user_to_area, name='add_user_to_area'),
    path('api/area/training/add/', views.add_training_area, name='add_training_area'),
    path('api/area/user/role/switch/', views.switch_user_role_in_area, name='switch_user_role_in_area'),
    path('api/area/user/delete/', views.delete_user_in_area, name='delete_user_in_area'),


    # Trainings - classes

    path('users/<int:user_id>/training-record/', views.UserTrainingsView.as_view(), name='user_trainings'),
    path('users/<int:user_id>/training-record/<int:training_id>/', views.UserTrainingDetailsView.as_view(), name='user_training_details'),

    # Trainings - functions

    path('all-trainings/', views.certs, name='all_trainings'),
    path('all-trainings/<int:cert_id>/edit/', views.edit_cert, name='edit_cert'),
    path('media/users/<int:user_id>/certificates/<int:cert_id>/<str:filename>/', views.download_user_cert),


    # Api


    path('api/users/<int:user_id>/certificates/', api_views.user_certs),


    path('api/labs/', api_views.labs),


    path('api/certificates/', api_views.certs),




    path('api/certificates/<int:cert_id>/delete/', api_views.delete_certs),
    path('saml/', saml_views.saml, name='saml'),
    path('attrs/', saml_views.attrs, name='attrs'),
    path('metadata/', saml_views.metadata, name='metadata'),


    # for testing

    path('labs/', views.labs, name='labs'),
    path('certs/', views.certs, name='certs'),
    path('api/users/', api_views.users),
    path('api/users/<int:user_id>/delete/', api_views.delete_user),
    path('api/users/<int:user_id>/switch_admin/', api_views.switch_admin),
    path('api/users/<int:user_id>/switch_inactive/', api_views.switch_inactive),
    path('api/users/<int:user_id>/certificates/<int:cert_id>/delete/', api_views.delete_user_certs),
    path('api/labs/<int:lab_id>/certificates/<int:cert_id>/delete/', api_views.delete_lab_certs),
    path('api/labs/<int:lab_id>/users/', api_views.user_labs),
    path('api/labs/<int:lab_id>/certificates/', api_views.lab_certs),

    path('accounts/local_login/', views.local_login, name='local_login'),
    #path('admin/', admin.site.urls),
    #path('accounts/admin/', include('django.contrib.auth.urls')),
    #path('error/<str:error_msg>/', views.show_error),
]

handler403 = views.permission_denied
handler404 = views.page_not_found
