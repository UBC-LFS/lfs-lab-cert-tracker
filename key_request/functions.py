from django.db.models.functions import Concat
from django.db.models import Q, F, Max, CharField, Value, Count, OuterRef, Subquery, Exists
from urllib.parse import urlparse
from django.forms.models import model_to_dict
from django.utils import timezone
from datetime import datetime, date
import re
import json


from django.contrib.auth.models import User
from lfs_lab_cert_tracker.models import Cert, LabCert
from .models import Building, Floor, Room, RequestForm, RequestFormStatus, ApprovalGroup, ApprovalGroupRole
from .utils import APPROVED, REV_REQUEST_STATUS_DICT


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


def is_room_approver(user_id):
    if Room.objects.count() == 0:
        return False
    return Room.objects.filter(Q(managers__id=user_id) | Q(groups__roles__user_id=user_id)).exists()

def is_approval_group_coordinator(user_id):
    if ApprovalGroup.objects.count() == 0:
        return False

    return ApprovalGroupRole.objects.filter(user_id=user_id, role=ApprovalGroupRole.Role.COORDINATOR).exists()

def preprocess_rooms(rooms):
    by_building = {}
    for room in rooms:
        if room.is_active:
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
                'key': r['key'],
                'fob': r['fob'],
                'alarm': r['alarm'],
                'areas': [{ 'id': area.id, 'name': area.name } for area in r['areas']],
                'trainings': [{ 'id': training.id, 'name': training.name } for training in r['trainings']]
            })

    return json.dumps(by_building)


def adjust_trainings_from_added_removed_areas(existing_training_ids, original_areas, new_areas):
    """ Remove trainings of previous areas and adds trainings of new areas"""
    removed_areas = set(original_areas) - set(new_areas)
    new_areas_set = set(new_areas)

    removed_certs = set(
        LabCert.objects.filter(lab_id__in=removed_areas)
        .values_list('cert_id', flat=True)
    )
    added_certs = set(
        LabCert.objects.filter(lab_id__in=new_areas_set)
        .values_list('cert_id', flat=True)
    )

    filtered_out = set(existing_training_ids) - removed_certs
    return list(filtered_out | added_certs)


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


def make_request_form_identifier(room, form, entity_label, entity_id):
    return f"{entity_label}:{entity_id}__{form.id}:{room.id}"


# Returns True if all PIs have approved a room; If there are no managers or groups, returns False
def all_pis_approved(form, room):

    if not room.managers.exists() and not room.groups.exists():
        return False

    # Managers: ALL approve
    manager_ids = room.managers.all().values_list("id", flat=True)
    num_managers = len(manager_ids)

    if num_managers > 0:
        latest_status = RequestFormStatus.objects.filter(
            form_id=form.id,
            room_id=room.id,
            manager_id=OuterRef("pk")
        ).order_by('-created_at')

        managers_with_status = (User.objects.filter(id__in=manager_ids).annotate(
            latest_status=Subquery(latest_status.values('status')[:1])
        ))

        approved_count = managers_with_status.filter(latest_status=APPROVED).count()
        if approved_count != num_managers:
            return False

    # Groups: at least one approve
    for group in room.groups.all():

        latest_status = RequestFormStatus.objects.filter(
            form_id=form.id,
            room_id=room.id,
            group_id=group.id
        ).order_by('-created_at').first()

        if latest_status is None or latest_status.status != APPROVED:
            return False

    return True

def get_area_ids_from_session(session, key, room=None):
    area_ids = [area.id for area in room.areas.all()] if room else []
    if session.get(key):
        if len(session[key]['areas']) > 0:
            area_ids = session[key]['areas']

    return area_ids

def create_data_from_session(session, key, room=None):
    data = model_to_dict(room) if room else {'building': '', 'floor': '', 'number': '', 'note': '', 'key': False, 'fob': False, 'alarm': False, 'is_active': True}
    manager_ids = [manager.id for manager in room.managers.all()] if room else []
    group_ids = [group.id for group in room.groups.all()] if room else []
    area_ids = [area.id for area in room.areas.all()] if room else []
    training_ids = [training.id for training in room.trainings.all()] if room else []

    if session.get(key):
        if session[key]['building']:
            data['building'] = session[key]['building']
        if session[key]['floor']:
            data['floor'] = session[key]['floor']
        if session[key]['number']:
            data['number'] = session[key]['number']

        if 'key' in session[key]:
            data['key'] = session[key]['key']
        if 'fob' in session[key]:
            data['fob'] = session[key]['fob']
        if 'alarm' in session[key]:
            data['alarm'] = session[key]['alarm']
        if 'is_active' in session[key]:
            data['is_active'] = session[key]['is_active']

        if session[key]['note']:
            data['note'] = session[key]['note']

        if len(session[key]['managers']) > 0:
            manager_ids = session[key]['managers']

        if len(session[key]['groups']) > 0:
            group_ids = session[key]['groups']

        if len(session[key]['areas']) > 0:
            area_ids = session[key]['areas']

        if len(session[key]['trainings']) > 0:
            training_ids = session[key]['trainings']

    return data, manager_ids, group_ids, area_ids, training_ids


def update_data_from_post_and_session(post, session, key, tab, room=None):
    data, manager_ids, group_ids, area_ids, training_ids = create_data_from_session(session, key, room)
    
    if tab == 'basic_info':
        if data['building'] != post.get('building'):
            data['building'] = post.get('building')
        if data['floor'] != post.get('floor'):
            data['floor'] = post.get('floor')
        if data['number'] != post.get('number'):
            data['number'] = post.get('number')

        key = True if post.get('key') else False
        if data['key'] != key:
            data['key'] = key

        fob = True if post.get('fob') else False
        if data['fob'] != fob:
            data['fob'] = fob

        alarm = True if post.get('alarm') else False
        if data['alarm'] != alarm:
            data['alarm'] = alarm

        is_active = True if post.get('is_active') else False
        if data['is_active'] != is_active:
            data['is_active'] = is_active

        if data['note'] != post.get('note'):
            data['note'] = post.get('note')

    elif tab == 'pis':
        managers = str_to_int(post.getlist('managers[]'))
        if not is_two_lists_equal(manager_ids, managers):
            manager_ids = managers
        groups = str_to_int(post.getlist('groups[]'))
        if not is_two_lists_equal(group_ids, groups):
            group_ids = groups

    elif tab == 'areas':
        areas = str_to_int(post.getlist('areas[]'))
        if not is_two_lists_equal(area_ids, areas):
            area_ids = areas

    elif tab == 'trainings':
        trainings = str_to_int(post.getlist('trainings[]'))
        if not is_two_lists_equal(training_ids, trainings):
            training_ids = trainings

    return data, manager_ids, group_ids, area_ids, training_ids

# GROUPS

def get_group_by_id(group_id):
    try:
        return ApprovalGroup.objects.prefetch_related('roles__user', 'group_rooms').get(id=group_id)
    except ApprovalGroup.DoesNotExist:
        return None

def get_all_groups():
    return ApprovalGroup.objects.all()

def get_all_user_groups(user):
    return ApprovalGroup.objects.filter(roles__user=user)

def get_group_member_ids(group):
    id_arr = group.members.values_list('id', flat=True)
    return [str(user_id) for user_id in id_arr]

def get_group_coordinator_ids(group):
    id_arr = group.coordinators.values_list('id', flat=True)
    return [str(user_id) for user_id in id_arr]

# Checks to see if a group with the same members & coordinators
def get_groups_with_matching_composition(member_ids, coordinator_ids, group_id=None, user_groups=None):
    # Normalize and deduplicate member ids (handles strings and duplicates)
    if not member_ids and not coordinator_ids:
        return ApprovalGroup.objects.none()

    try:
        member_ids = [int(m) for m in member_ids]
        coordinator_ids = [int(c) for c in coordinator_ids]
    except Exception:
        member_ids = list(member_ids)
        coordinator_ids = list(coordinator_ids)

    seen = set()
    unique_member_ids = []
    role_map = {}
    for m in member_ids:
        if m not in seen:
            seen.add(m)
            unique_member_ids.append(m)
            role_map[m] = ApprovalGroupRole.Role.MEMBER

    for m in coordinator_ids:
        if m not in seen:
            seen.add(m)
            unique_member_ids.append(m)
        role_map[m] = ApprovalGroupRole.Role.COORDINATOR


    num_members = len(unique_member_ids)

    if not user_groups:
        user_groups = ApprovalGroup.objects.all()

    group_matches = user_groups.annotate(
        total_members=Count('roles__user_id', distinct=True)
    ).filter(total_members=num_members)

    for member_id in unique_member_ids:
        group_matches = group_matches.filter(roles__user_id=member_id, roles__role=role_map.get(member_id))

    if group_id:
        group_matches = group_matches.exclude(id=group_id)

    return group_matches.prefetch_related('roles__user').distinct()

def get_group_with_matching_name(group_name, group_id=None):
    matching_groups = ApprovalGroup.objects.filter(name__iexact=group_name)

    if group_id:
        matching_groups = matching_groups.exclude(id=group_id)

    return matching_groups

# END GROUPS

def natural_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def search_filter_options():
    rooms = Room.objects.values_list('number', flat=True)
    return {
        'buildings': Building.objects.values('code'),
        'floors': Floor.objects.values('name'),
        'rooms': sorted(set(rooms), key=natural_key)
    }


# Helper

def is_two_lists_equal(l1, l2):
    return set(l1) == set(l2)


def display_user_full_name(user):
    return user.get_full_name() if user.first_name and user.last_name else user.username


def display_user_first_name(user):
    return user.first_name if user.first_name else user.username


def display_room(room, option=None):
    ret = '{0} {1} - Room {2}'.format(room.building.code, room.floor.name, room.number)
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

def convert_date_to_str(date):
    return date.strftime('%Y-%m-%d')


def convert_str_to_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def has_date_passed(date_obj):
    if not date_obj:
        return False

    return date_obj < timezone.localdate()

