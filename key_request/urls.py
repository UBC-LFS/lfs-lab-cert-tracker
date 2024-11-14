from django.urls import path
from . import views

app_name = 'key_request'

urlpatterns = [

    # Admin
    path('all-requests/', views.AllRequests.as_view(), name='all_requests'),
    
    # Rooms

    path('create-room/', views.CreateRoom.as_view(), name='create_room'),
    path('all-rooms/edit/', views.edit_room, name='edit_room'),
    path('all-rooms/delete/', views.delete_room, name='delete_room'),
    path('all-rooms/', views.AllRooms.as_view(), name='all_rooms'),

    path('api/room/managers/change/', views.change_room_managers, name='change_room_managers'),
    path('api/room/areas/change/', views.change_room_areas, name='change_room_areas'),
    path('api/room/trainings/change/', views.change_room_trainings, name='change_room_trainings'),

    # Settings - Building and Floors
    path('all-<str:model>/delete/', views.DeleteSetting.as_view(), name='delete_setting'),
    path('all-<str:model>/edit/', views.EditSetting.as_view(), name='edit_setting'),
    path('all-<str:model>/', views.Settings.as_view(), name='settings'),

    # Form Submission process
    path('rooms/select/step1/', views.SelectRooms.as_view(), name='select_rooms'),
    path('user-trainings/check/step2/', views.CheckUserTrainings.as_view(), name='check_user_trainings'),
    path('form/submit/step3/', views.SubmitForm.as_view(), name='submit_form'),

    path('forms/<int:form_id>/details/', views.ViewFormDetails.as_view(), name='view_form_details'),

    path('pi-rooms/', views.ManagerRooms.as_view(), name='manager_rooms'),
    path('pi-dashboard/', views.ManagerDashboard.as_view(), name='manager_dashboard'),
    

    

    path('func/update/all/', views.update_all, name='update_all'),
    path('', views.Index.as_view(), name='index')
]