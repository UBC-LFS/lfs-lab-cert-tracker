from django.urls import path
from . import views
from . import admin_views
from . import manager_views
from . import process_views

app_name = 'key_request'


urlpatterns = [
    path('', views.Index.as_view(), name='index')
]


# Admin
urlpatterns += [
    path('requests/all/', admin_views.AllRequests.as_view(), name='all_requests'),
    path('requests/expired/', admin_views.ExpiredRequests.as_view(), name='expired_requests'),
    path('forms/<int:form_id>/details/', admin_views.ViewFormDetails.as_view(), name='view_form_details'),
    path('func/update/all/', admin_views.update_all, name='update_all'),
    path('func/emails/send/', admin_views.send_emails, name='send_emails'),

    # Rooms
    path('all-rooms/', admin_views.AllRooms.as_view(), name='all_rooms'),
    path('create-room/', admin_views.CreateRoom.as_view(), name='create_room'),
    path('<int:room_id>/edit-room/', admin_views.EditRoom.as_view(), name='edit_room'),
    path('all-rooms/delete/', admin_views.delete_room, name='delete_room'),

    # Groups
    path('manager-groups/', manager_views.ViewManagerApprovalGroups.as_view(), name='manager_groups'),
    path('all-groups/', admin_views.ViewAllApprovalGroups.as_view(), name='all_groups'),
    path('<int:group_id>/edit-group/', admin_views.EditApprovalGroups.as_view(), name='edit_group'),
    path('<int:group_id>/manage-group/', manager_views.EditManagerGroups.as_view(), name='manager_edit_group'),
    path('all-groups/change-activation/', admin_views.change_group_activation, name='change_activation'),

    path('<int:group_id>/change-member-role/', manager_views.change_group_member_role, name='change_group_member_role'),
    path('<int:group_id>/delete-member/', manager_views.delete_group_member, name='delete_group_member'),
    path('create-group', admin_views.CreateApprovalGroup.as_view(), name='create_group'),
    path('user_autofill/', admin_views.user_autofill_suggestions, name='user_autofill'),
    path('validate_room_group/', admin_views.validate_approval_group, name='validate_room_group'),

    # Settings - Building and Floors
    path('all-<str:model>/view/', admin_views.Settings.as_view(), name='settings'),
    path('all-<str:model>/edit/', admin_views.EditSetting.as_view(), name='edit_setting'),
    path('all-<str:model>/delete/', admin_views.DeleteSetting.as_view(), name='delete_setting'),
    
    path('add-training-to-room/', admin_views.AddTrainingToRoom.as_view(), name='add_training_to_room'),
    path('delete-training-from-room/', admin_views.DeleteTrainingFromRoom.as_view(), name='delete_training_from_room')
]


# Managers
urlpatterns += [
    path('rooms/', manager_views.ManagerRooms.as_view(), name='manager_rooms'),
    path('dashboard/expiry-date/update/', manager_views.UpdateExpiryDate.as_view(), name='update_expiry_date'),
    path('dashboard/', manager_views.ManagerDashboard.as_view(), name='manager_dashboard')
]


# Key Request process
urlpatterns += [
    path('rooms/select/step1/', process_views.SelectRooms.as_view(), name='select_rooms'),
    path('user-trainings/check/step2/', process_views.CheckUserTrainings.as_view(), name='check_user_trainings'),
    path('form/submit/step3/', process_views.SubmitForm.as_view(), name='submit_form')
]