from django.urls import path
from . import views

app_name = 'app'

urlpatterns = [

    # Settings - classes
    path('settings/', views.SettingIndex.as_view(), name='setting_index'),
    
    path('all-areas/', views.AllAreas.as_view(), name='all_areas'),
    path('create-area/', views.CreateArea.as_view(), name='create_area'),

    path('all-trainings/', views.AllTrainings.as_view(), name='all_trainings'),
    path('create-training/', views.CreateTraining.as_view(), name='create_training'),
    
    path('all-users/', views.AllUsers.as_view(), name='all_users'),
    path('create-user/', views.CreateUser.as_view(), name='create_user'),
    path('user-report/', views.UserReportMissingTrainings.as_view(), name='user_report_missing_trainings'),
    path('api-updates/', views.APIUpdates.as_view(), name='api_updates'),


    # Users - classes
    path('users/<int:user_id>/work-area/', views.UserAreasView.as_view(), name='user_areas'),
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


    # Areas - classes
    
    path('areas/<int:area_id>/', views.AreaDetailsView.as_view(), name='area_details'),


    # Areas - api
    path('api/area/update/', views.edit_area, name='edit_area'),
    path('api/area/delete/', views.delete_area, name='delete_area'),
    path('api/area/training/delete/', views.delete_training_in_area, name='delete_training_in_area'),
    path('api/area/training/add/', views.add_training_area, name='add_training_area'),
    path('api/area/<int:area_id>/user/role/switch/', views.switch_user_role_in_area, name='switch_user_role_in_area'),
    path('api/area/<int:area_id>/user/delete/', views.delete_user_in_area, name='delete_user_in_area'),


    # Trainings - apis
    path('api/trainings/edit/', views.edit_training, name='edit_training'),
    path('api/trainings/delete/', views.delete_training, name='delete_training'),
    #path('api/users/<int:user_id>/training/delete/', views.delete_user_training, name='delete_user_training'),

    path('media/users/<int:user_id>/certificates/<int:cert_id>/<str:filename>/', views.download_user_cert),

    path('', views.index, name='index')
]
