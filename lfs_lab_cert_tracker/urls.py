from django.urls import path, include
from django.conf.urls import handler400, handler403, handler404, handler500
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from lfs_lab_cert_tracker import views

urlpatterns = [

    # Users - classes
    path('app/users/report/missing-trainings/', views.UserReportMissingTrainingsView.as_view(), name='user_report_missing_trainings'),
    path('app/users/new/', views.NewUserView.as_view(), name='new_user'),
    path('app/users/all/', views.AllUsersView.as_view(), name='all_users'),
    path('app/users/<int:user_id>/work-area/', views.UserAreasView.as_view(), name='user_areas'),
    path('app/users/<int:user_id>/', views.UserDetailsView.as_view(), name='user_details'),
    path('app/users/<int:user_id>/training-record/', views.UserTrainingsView.as_view(), name='user_trainings'),
    path('app/users/<int:user_id>/training-record/<int:training_id>/', views.UserTrainingDetailsView.as_view(), name='user_training_details'),

    # Users - functions
    path('app/users/<int:user_id>/report.pdf/', views.user_report, name='user_report'),
    path('app/users/report/missing-trainings/download/', views.download_user_report_missing_trainings, name='download_user_report_missing_trainings'),


    # Users - api
    path('app/api/user/delete/', views.delete_user, name='delete_user'),
    path('app/api/user/switch-admin/', views.switch_admin, name='switch_admin'),
    path('app/api/user/switch-inactive/', views.switch_inactive, name='switch_inactive'),
    path('app/api/users/assign/areas/', views.assign_user_areas, name='assign_user_areas'),
    path('app/api/users/<int:user_id>/read/welcome-message/', views.read_welcome_message, name="read_welcome_message"),


    # Areas - classes
    path('app/areas/all/', views.AllAreasView.as_view(), name='all_areas'),
    path('app/areas/<int:area_id>/', views.AreaDetailsView.as_view(), name='area_details'),


    # Areas - api
    path('app/api/area/update/', views.edit_area, name='edit_area'),
    path('app/api/area/delete/', views.delete_area, name='delete_area'),
    path('app/api/area/training/delete/', views.delete_training_in_area, name='delete_training_in_area'),
    path('app/api/area/training/add/', views.add_training_area, name='add_training_area'),
    path('app/api/area/<int:area_id>/user/role/switch/', views.switch_user_role_in_area, name='switch_user_role_in_area'),
    path('app/api/area/<int:area_id>/user/delete/', views.delete_user_in_area, name='delete_user_in_area'),


    # Trainings - classes
    path('app/trainings/all/', views.AllTrainingsView.as_view(), name='all_trainings'),

    # Trainings - apis
    path('app/api/trainings/edit/', views.edit_training, name='edit_training'),
    path('app/api/trainings/delete/', views.delete_training, name='delete_training'),
    path('app/api/users/<int:user_id>/training/delete/', views.delete_user_training, name='delete_user_training'),

    path('media/users/<int:user_id>/certificates/<int:cert_id>/<str:filename>/', views.download_user_cert),

    path('', views.landing_page, name='landing_page')
]

if settings.DEBUG:
    urlpatterns += [
        path('admin/', admin.site.urls)
    ]

if settings.LOCAL_LOGIN:
    urlpatterns += [
        path('accounts/local-login/', views.local_login, name='local_login')
    ]

handler400 = views.bad_request
handler403 = views.permission_denied
handler404 = views.page_not_found
handler500 = views.internal_server_error
