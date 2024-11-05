from django.urls import path, include
from django.conf.urls import handler400, handler403, handler404, handler500
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from lfs_lab_cert_tracker import views

urlpatterns = [
    path('accounts/', include('accounts.urls')),
    path('app/', include('app.urls')),
    path('app/key-request/', include('key_request.urls')),
    path('', views.landing_page, name='landing_page')
]

if settings.DEBUG:
    urlpatterns += [
        path('admin/', admin.site.urls)
    ]

handler400 = views.bad_request
handler403 = views.permission_denied
handler404 = views.page_not_found
handler500 = views.internal_server_error
