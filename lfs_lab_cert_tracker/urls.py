"""lfs_lab_cert_tracker URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin

from lfs_lab_cert_tracker import views

urlpatterns = [
    url(r'^admin/', admin.site.urls),

    url(r'^api/labs/', views.labs),
    url(r'^api/labs/<int:lab_id>/', views.labs),

    url(r'^api/certificates/', views.certificates),
    url(r'^api/certificates/<int:cert_id>/', views.certificates),

    url(r'^api/labs/<int:lab_id>/certificates/', views.lab_certificates),
    url(r'^api/labs/<int:lab_id>/certificates/<int:cert_id>', views.lab_certificates),

    # url(r'^api/users/<int:user_id/certificates/', views.user_certificates),
    # url(r'^api/users/<int:user_id>/certificates/<int:cert_id>', views.user_certificates),
]

urlpatterns += [
    url(r'^accounts/', include('django.contrib.auth.urls')),
]
