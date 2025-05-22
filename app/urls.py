from django.urls import path

from . import views
from . import settings_views
from . import users_views
from . import area_details_views

app_name = 'app'

urlpatterns = [
    path('func/users/<int:user_id>/read/welcome-message/', views.read_welcome_message, name="read_welcome_message"),
    path('media/users/<int:user_id>/certificates/<int:cert_id>/<str:filename>/download/', views.download_user_cert),
    path('', views.index, name='index')
]


urlpatterns += [
    path('users/<int:user_id>/my-account/', users_views.MyAccount.as_view(), name='my_account'),
    path('users/<int:user_id>/my-work-area/', users_views.MyWorkArea.as_view(), name='my_work_area'),
    path('users/<int:user_id>/my-training-record/', users_views.MyTrainingRecord.as_view(), name='my_training_record'),
    path('users/<int:user_id>/add-training-record/', users_views.AddTrainingRecord.as_view(), name='add_training_record'),
    path('users/<int:user_id>/training-record/<int:training_id>/details/', users_views.TrainingDetailsView.as_view(), name='training_details'),

    path('users/<int:user_id>/report.pdf/', users_views.user_report, name='user_report'),
]


urlpatterns += [
    path('settings/', settings_views.Index.as_view(), name='setting_index'),

    path('all-areas/', settings_views.AllAreas.as_view(), name='all_areas'),
    path('create-area/', settings_views.CreateArea.as_view(), name='create_area'),
    path('func/area/update/', settings_views.edit_area, name='edit_area'),
    path('func/area/delete/', settings_views.delete_area, name='delete_area'),

    path('all-trainings/', settings_views.AllTrainings.as_view(), name='all_trainings'),
    path('func/trainings/edit/', settings_views.edit_training, name='edit_training'),
    path('func/trainings/delete/', settings_views.delete_training, name='delete_training'),
    path('create-training/', settings_views.CreateTraining.as_view(), name='create_training'),

    path('all-users/', settings_views.AllUsers.as_view(), name='all_users'),

    path('func/user/delete/', settings_views.delete_user, name='delete_user'),
    path('func/user/switch-admin/', settings_views.switch_admin, name='switch_admin'),
    path('func/user/switch-inactive/', settings_views.switch_inactive, name='switch_inactive'),
    path('func/users/assign/areas/', settings_views.assign_user_areas, name='assign_user_areas'),

    path('create-user/', settings_views.CreateUser.as_view(), name='create_user'),
    path('user-report/', settings_views.UserReportMissingTrainings.as_view(), name='user_report_missing_trainings'),
    path('users/report/missing-trainings/download.pdf/', settings_views.download_user_report_missing_trainings, name='download_user_report_missing_trainings'),
    path('api-updates/', settings_views.APIUpdates.as_view(), name='api_updates')
]


urlpatterns += [
    path('areas/<int:area_id>/area-details/', area_details_views.Index.as_view(), name='area_details'),
    path('areas/<int:area_id>/users-missing-training-record/', area_details_views.UsersMissingTrainings.as_view(), name='users_missing_trainings'),
    path('areas/<int:area_id>/users-expired-training-record/', area_details_views.UsersExpiredTrainings.as_view(), name='users_expired_trainings'),
    path('areas/<int:area_id>/add-user-to-area/', area_details_views.AddUserToArea.as_view(), name='add_user_to_area'),
    path('areas/<int:area_id>/add-training-to-area/', area_details_views.AddTrainingToArea.as_view(), name='add_training_to_area'),

    path('func/area/training/delete/', area_details_views.delete_training_in_area, name='delete_training_in_area'),
    path('func/area/<int:area_id>/user/role/switch/', area_details_views.switch_user_role_in_area, name='switch_user_role_in_area'),
    path('func/area/<int:area_id>/user/delete/', area_details_views.delete_user_in_area, name='delete_user_in_area')
]
