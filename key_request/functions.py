import json
from django.db.models import Q, F, Max
from datetime import date

from .models import *
from django.forms.models import model_to_dict


def get_headers(model):
    headers = []
    # exceptions = ['id', 'created_on', 'updated_on', 'slug']
    exceptions = ['slug']
    for field in model._meta.fields:
        if field.name not in exceptions:
            name = field.name
            if field.name == 'id':
                name = 'ID'
            else:
                name = field.name.capitalize()
            headers.append(name)
    headers.append('Actions')
    return headers


def preprocess_rooms(rooms):
    by_building = {}
    for room in rooms:
        r = model_to_dict(room)

        building_id = r['building']
        floor_id = r['floor']
        floor = Floor.objects.get(id=floor_id)
        floor_dict = { 'id': floor.id, 'name': floor.name, 'numbers': [] }

        if building_id not in by_building.keys():
            by_building[building_id] = {}
        
        if floor_id not in by_building[building_id].keys():
            by_building[building_id][floor_id] = floor_dict

        by_building[building_id][floor_id]['numbers'].append({ 
            'id': r['id'], 
            'number': r['number'], 
            'areas': [{ 'id': area.id, 'name': area.name } for area in r['areas']],
            'trainings': [{ 'id': training.id, 'name': training.name } for training in r['trainings']]
        })
    
    return json.dumps(by_building)


def check_user_trainings(user, selected_rooms):
    required_trainings = []
    for room_id in selected_rooms:
        room = Room.objects.get(id=room_id)
        
        for training in room.trainings.all():
            if training not in required_trainings:
                required_trainings.append(training)
    
    certs = Cert.objects.filter(usercert__user_id=user.id).distinct()
    missing_ids = [m.id for m in set(required_trainings).difference(set(certs))]

    expired = user.usercert_set.values('cert_id').annotate(max_expiry_date=Max('expiry_date')).filter( Q(max_expiry_date__lt=date.today()) & ~Q(completion_date=F('expiry_date')) )
    expired_ids = [e['cert_id'] for e in expired]

    total_missing = 0
    total_expired = 0
    for tr in required_trainings:
        tr.is_missing = False
        tr.is_expired = False

        if tr.id in missing_ids:
            tr.is_missing = True
            total_missing += 1

        if tr.id in expired_ids:
            tr.is_expired = True
            total_expired += 1
    
    return sorted(required_trainings, key=lambda x: x.name, reverse=False), total_missing, total_expired


def get_manager_dashboard(user):
    requests = []
    new_requests = 0
    for form in RequestForm.objects.all():
        for room in form.rooms.all():
            room_flitered = room.managers.filter(id__in=[user.id])
            if room_flitered.exists():
                form.room = room
                
                user_trainings, total_missing, total_expired = check_user_trainings(form.user, [room.id for room in form.rooms.all()])
                form.user_trainings = user_trainings
                form.total_missing = total_missing
                form.total_expired = total_expired

                status = None
                status_filtered = form.requestformstatus_set.filter(form_id=form.id, room_id=room.id, manager_id=user.id)
                if status_filtered.exists():
                    status = status_filtered
                else:
                    new_requests += 1

                requests.append({ 
                    'form': form, 
                    'room': room, 
                    'manager': {
                        'id': user.id, 
                        'full_name': user.get_full_name()
                    },
                    'status': status
                })
    
    return requests, new_requests