from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET
from django.urls import resolve
from urllib.parse import urlparse

from lfs_lab_cert_tracker.models import Cert
from .models import Building, Floor, Room


class RoomActionsMixin:

    @method_decorator(require_GET)
    def get(self, request, *args, **kwargs):
        parsed = urlparse(request.get_full_path())
        url_name = resolve(parsed.path).url_name
        template = 'key_request/admin/{0}.html'.format(url_name)

        room_numbers = list(set(Room.objects.values_list('number', flat=True)))
        room_numbers.sort(key=lambda a: int(a))
        
        return render(request, template, {
            'rooms': Room.objects.all(),
            'buildings': Building.objects.all(),
            'floors': Floor.objects.all(),
            'trainings': Cert.objects.all(),
            'room_numbers': room_numbers,
        })