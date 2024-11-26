import json
from django.db.models import Q, F, Max
from urllib.parse import urlparse
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


def search_filters_for_requests(query):
    forms = RequestForm.objects.all()
    new_forms = forms.filter(requestformstatus__isnull=True)

    total = len(forms)
    if query:
        if query['building']:
            forms = forms.filter(rooms__building__code__icontains=query['building']).distinct()
        if query['floor']:
            forms = forms.filter(rooms__floor__name__icontains=query['floor']).distinct()
        if query['number']:
            forms = forms.filter(rooms__number__icontains=query['number']).distinct()
        if query['name']:
            forms = forms.filter(Q(user__first_name__icontains=query['name']) | Q(user__last_name__icontains=query['name'])).distinct()

    return forms, total, new_forms


def get_manager_dashboard(user, query=None):
    forms, _, _ = search_filters_for_requests(query)
    total_requests = 0
    requests = []
    num_new_requests = 0
    for form in forms:
        for room in form.rooms.all():
            is_valid = True
            room_flitered = room.managers.filter(id__in=[user.id])
            if room_flitered.exists():
                total_requests += 1
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
                    num_new_requests += 1

                if query and query['status']:
                    if query['status'] == 'New':
                        if status:
                            is_valid = False
                    else:
                        if status:
                            if query['status'] in REV_REQUEST_STATUS_DICT.keys() and (REV_REQUEST_STATUS_DICT[query['status']] != status.last().status):
                                is_valid = False
                        else:
                            is_valid = False
                
                if is_valid:
                    requests.append({ 
                        'form': form, 
                        'room': room, 
                        'manager': {
                            'id': user.id, 
                            'full_name': user.get_full_name()
                        },
                        'status': status
                    })
    
    return requests, total_requests, num_new_requests


def str_to_int(l):
    if len(l) > 0:
        return [int(a) for a in l]
    return []


def update_room_data(tab, post, data):
    if tab == 'basic_info':
        data['building'] = post.get('building')
        data['floor'] = post.get('floor')
        data['number'] = post.get('number')

    elif tab == 'pis':
        data['managers'] = str_to_int(post.getlist('managers[]'))

    elif tab == 'areas':
        data['areas'] = str_to_int(post.getlist('areas[]'))

    elif tab == 'trainings':
        data['trainings'] = str_to_int(post.getlist('trainings[]'))
    
    return data

def get_next(request):
    full_path = request.get_full_path()
    parse_result = urlparse(full_path)
    query = parse_result.query.split('next=')
    if len(query) > 1:
        return query[1]
    return None