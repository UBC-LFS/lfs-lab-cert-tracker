from django.urls import path

from . import views
from . import settings_views
from . import area_details_views

app_name = 'app'

urlpatterns = [

    # Settings

    path('settings/', settings_views.Index.as_view(), name='setting_index'),
    
    path('all-areas/', settings_views.AllAreas.as_view(), name='all_areas'),
    path('create-area/', settings_views.CreateArea.as_view(), name='create_area'),
    path('func/area/update/', settings_views.edit_area, name='edit_area'),
    path('func/area/delete/', settings_views.delete_area, name='delete_area'),

    path('all-trainings/', settings_views.AllTrainings.as_view(), name='all_trainings'),
    path('create-training/', settings_views.CreateTraining.as_view(), name='create_training'),
    
    path('all-users/', settings_views.AllUsers.as_view(), name='all_users'),
    path('create-user/', settings_views.CreateUser.as_view(), name='create_user'),
    path('user-report/', settings_views.UserReportMissingTrainings.as_view(), name='user_report_missing_trainings'),
    path('api-updates/', settings_views.APIUpdates.as_view(), name='api_updates'),


    # Area Details

    path('areas/<int:area_id>/area-details/', area_details_views.Index.as_view(), name='area_details'),
    path('areas/<int:area_id>/users-missing-training-record/', area_details_views.UsersMissingTrainings.as_view(), name='users_missing_trainings'),
    path('areas/<int:area_id>/users-expired-training-record/', area_details_views.UsersExpiredTrainings.as_view(), name='users_expired_trainings'),
    path('areas/<int:area_id>/add-user-to-area/', area_details_views.AddUserToArea.as_view(), name='add_user_to_area'),
    path('areas/<int:area_id>/add-training-to-area/', area_details_views.AddTrainingToArea.as_view(), name='add_training_to_area'),

    path('func/area/training/delete/', area_details_views.delete_training_in_area, name='delete_training_in_area'),
    path('func/area/<int:area_id>/user/role/switch/', area_details_views.switch_user_role_in_area, name='switch_user_role_in_area'),
    path('func/area/<int:area_id>/user/delete/', area_details_views.delete_user_in_area, name='delete_user_in_area'),



    # Users - classes
    path('users/<int:user_id>/work-area/', views.UserAreas.as_view(), name='user_areas'),
    path('users/<int:user_id>/', views.UserDetails.as_view(), name='user_details'),
    path('users/<int:user_id>/my-training-record/', views.MyTrainingRecord.as_view(), name='my_training_record'),
    path('users/<int:user_id>/add-training-record/', views.AddTrainingRecord.as_view(), name='add_training_record'),
    path('users/<int:user_id>/training-record/<int:training_id>/', views.UserTrainingDetailsView.as_view(), name='user_training_details'),


    # Users - functions
    path('users/<int:user_id>/report.pdf/', views.user_report, name='user_report'),
    path('users/report/missing-trainings/download.pdf/', views.download_user_report_missing_trainings, name='download_user_report_missing_trainings'),


    # Users - api
    path('api/user/delete/', views.delete_user, name='delete_user'),
    path('api/user/switch-admin/', views.switch_admin, name='switch_admin'),
    path('api/user/switch-inactive/', views.switch_inactive, name='switch_inactive'),
    path('api/users/assign/areas/', views.assign_user_areas, name='assign_user_areas'),
    path('api/users/<int:user_id>/read/welcome-message/', views.read_welcome_message, name="read_welcome_message"),
    

    # Trainings - apis
    path('api/trainings/edit/', views.edit_training, name='edit_training'),
    path('api/trainings/delete/', views.delete_training, name='delete_training'),
    #path('api/users/<int:user_id>/training/delete/', views.delete_user_training, name='delete_user_training'),

    path('media/users/<int:user_id>/certificates/<int:cert_id>/<str:filename>/', views.download_user_cert),

    path('', views.index, name='index')
]
