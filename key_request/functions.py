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
            'is_active': r['is_active'],
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
            forms = forms.filter(rooms__building__code__exact=query['building']).distinct()
        if query['floor']:
            forms = forms.filter(rooms__floor__name__exact=query['floor']).distinct()
        if query['number']:
            forms = forms.filter(rooms__number__exact=query['number']).distinct()
        if query['room']:
            forms = forms.filter(rooms__id__exact=query['room']).distinct()
        if query['name']:
            forms = forms.filter(Q(user__first_name__icontains=query['name']) | Q(user__last_name__icontains=query['name'])).distinct()

    return forms, total, new_forms


def get_forms_per_manager(manager):
    rooms_managed = Room.objects.filter(managers=manager)
    return RequestForm.objects.filter(rooms__in=rooms_managed)


def get_manager_dashboard(manager, query=None):
    rooms_managed = Room.objects.filter(managers=manager)
    form_filtered = RequestForm.objects.filter(rooms__in=rooms_managed)
    total_forms = form_filtered.count()

    num_new_forms = 0
    for form in form_filtered.all():
        if form.requestformstatus_set.filter(operator_id=manager.id).count() == 0:
            num_new_forms += 1

    if query:
        if query['building']:
            rooms_managed = rooms_managed.filter(building__code__exact=query['building'])
        if query['floor']:
            rooms_managed = rooms_managed.filter(floor__name__exact=query['floor'])
        if query['number']:
            rooms_managed = rooms_managed.filter(number__exact=query['number'])

    forms = []
    for room in rooms_managed.all():
        all_forms = room.requestform_set.all()
        for form in all_forms:
            form.manager = manager
            form.room = room
            form.status = form.requestformstatus_set.filter(operator_id=manager.id)

            if query and query['status']:
                if form.status.count() == 0:
                    if query['status'] == 'New':
                        forms.append(form)
                else:
                    if (query['status'] in REV_REQUEST_STATUS_DICT.keys()) and (form.status.last().status == REV_REQUEST_STATUS_DICT[query['status']]):
                        forms.append(form)
            else:
                forms.append(form)

    forms = sorted(forms, key=lambda x: x.id, reverse=True)
    return total_forms, num_new_forms, forms


def create_data_from_session(session, key, room=None):
    data = model_to_dict(room) if room else {'building': '', 'floor': '', 'number': '', 'is_active': True}
    manager_ids = [manager.id for manager in room.managers.all()] if room else []
    area_ids = [area.id for area in room.areas.all()] if room else []
    training_ids = [training.id for training in room.trainings.all()] if room else []
    
    if session.get(key):
        if session[key]['building']:
            data['building'] = session[key]['building']
        if session[key]['floor']:
            data['floor'] = session[key]['floor']
        if session[key]['number']:
            data['number'] = session[key]['number']
        if session[key]['is_active']:
            data['is_active'] = session[key]['is_active']

        if len(session[key]['managers']) > 0:
            manager_ids = session[key]['managers']

        if len(session[key]['areas']) > 0:
            area_ids = session[key]['areas']

        if len(session[key]['trainings']) > 0:
            training_ids = session[key]['trainings']
    
    return data, manager_ids, area_ids, training_ids


def update_data_from_post_and_session(post, session, key, tab, room=None):
    data, manager_ids, area_ids, training_ids = create_data_from_session(session, key, room)
    print(data)
    if tab == 'basic_info':
        if data['building'] != post.get('building'):
            data['building'] = post.get('building')
        if data['floor'] != post.get('floor'):
            data['floor'] = post.get('floor')
        if data['number'] != post.get('number'):
            data['number'] = post.get('number')
        
        is_active = True if post.get('is_active') else False
        if data['is_active'] != is_active:
            data['is_active'] = is_active
    
    elif tab == 'pis':
        managers = str_to_int(post.getlist('managers[]'))
        if not is_two_lists_equal(manager_ids, managers):
            manager_ids = managers

    elif tab == 'areas':
        areas = str_to_int(post.getlist('areas[]'))
        if not is_two_lists_equal(area_ids, areas):
            area_ids = areas

    elif tab == 'trainings':
        trainings = str_to_int(post.getlist('trainings[]'))
        if not is_two_lists_equal(training_ids, trainings):
            training_ids = trainings

    return data, manager_ids, area_ids, training_ids


def is_two_lists_equal(l1, l2):
    return set(l1) == set(l2)


def display_room(room, option=None):
    ret = '{} {} - Room {}'.format(room.building.code, room.floor.name, room.number, room.id)
    if option == 'id':
        ret += f' (ID: {room.id})'
    return ret


def str_to_int(l):
    if len(l) > 0:
        return [int(a) for a in l]
    return []


def get_next(request):
    full_path = request.get_full_path()
    parse_result = urlparse(full_path)
    query = parse_result.query.split('next=')
    if len(query) > 1:
        return query[1]
    return None


def get_tab_urls(url, next=''):
    return {
        'basic_info': url + 'basic_info&next=' + next,
        'pis': url + 'pis&next=' + next,
        'areas': url + 'areas&next=' + next,
        'trainings': url + 'trainings&next=' + next
    }