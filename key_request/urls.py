from django.urls import path
from . import views

app_name = 'key_request'

urlpatterns = [

    # Rooms
    path('all-rooms/', views.AllRooms.as_view(), name='all_rooms'),
    path('api/rooms/edit/', views.edit_room, name='edit_room'),
    path('api/rooms/delete/', views.delete_room, name='delete_room'),
    path('create-room/', views.CreateRoom.as_view(), name='create_room'),

    path('api/room/managers/change/', views.change_room_managers, name='change_room_managers'),
    path('api/room/areas/change/', views.change_room_areas, name='change_room_areas'),
    path('api/room/trainings/change/', views.change_room_trainings, name='change_room_trainings'),

    # Building
    path('building/delete/', views.delete_course_code, name='delete_building'),
    path('building/edit/', views.edit_course_code, name='edit_building'),
    path('all-buildings/', views.AllBuildings.as_view(), name='all_buildings'),

    # Form Submission process
    path('rooms/select/step1/', views.SelectRooms.as_view(), name='select_rooms'),
    path('user-trainings/check/step2/', views.CheckUserTrainings.as_view(), name='check_user_trainings'),
    path('form/submit/step3/', views.SubmitForm.as_view(), name='submit_form'),

    path('forms/<int:form_id>/details/', views.ViewFormDetails.as_view(), name='view_form_details'),

    path('pi-rooms/', views.ManagerRooms.as_view(), name='manager_rooms'),
    path('pi-dashboard/', views.ManagerDashboard.as_view(), name='manager_dashboard'),
    path('all-requests/', views.AllRequests.as_view(), name='all_requests'),

    # Settings
    path('settings/<str:model>/', views.Settings.as_view(), name='settings'),
    path('settings/<str:model>/edit/', views.EditSettings.as_view(), name='edit_settings'),
    path('settings/<str:model>/delete/', views.DeleteSettings.as_view(), name='delete_settings'),

    path('func/update/all/', views.update_all, name='update_all'),
    path('', views.Index.as_view(), name='index')
]