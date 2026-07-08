from django.db.models.functions import Concat
from django.db.models import Q, F, Max, CharField, Value, Count, OuterRef, Subquery, Exists
from urllib.parse import urlparse
from django.forms.models import model_to_dict
from django.utils import timezone
from datetime import datetime, date
import re
import json


from django.contrib.auth.models import User
from lfs_lab_cert_tracker.models import Cert
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
    return Room.objects.filter(Q(managers__id=user_id) | Q(groups__roles__user_id=user_id))


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


def search_filters_for_requests(query, option=None):
    forms = RequestForm.objects.all()

    if option == 'expiry':
        forms = RequestForm.objects.select_related('user', 'supervisor').filter(
            expiry_date__isnull=False,
            expiry_date__lt=timezone.localdate()
        ).order_by('-expiry_date', '-id')

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
            forms = filter_forms_by_full_name(forms, query.get('name'))
            # forms = forms.filter(Q(user__first_name__icontains=query['name'].strip()) | Q(user__last_name__icontains=query['name'].strip())).distinct()
        if query['status']:
            if query['status'] == "New":
                forms = forms.filter(requestformstatus__isnull=True)
            else:
                forms = forms.filter(requestformstatus__status__exact=REV_REQUEST_STATUS_DICT.get(query['status'])).distinct()

    return forms, total, new_forms


# Takes the name search term and looks for partial matches of users' full names
def filter_forms_by_full_name(forms, name):
    return forms.annotate(
        full_name = Concat(F('user__first_name'), Value(' '), F('user__last_name'), output_field=CharField())
    ).filter(
        Q(full_name__icontains=name)
    ).distinct()


def get_forms_per_manager(user):
    # rooms_managed = Room.objects.filter(managers=user)
    # return RequestForm.objects.filter(rooms__in=rooms_managed)
    return RequestForm.objects.filter(rooms__managers=user)

def make_request_form_identifier(room, form, entity_label, entity_id):
    return f"{entity_label}:{entity_id}__{form.id}:{room.id}"

def get_manager_dashboard(user, query=None):
    if Room.objects.count() == 0:
        return 0, 0, []

    rooms_managed = Room.objects.filter(managers=user)
    form_filtered = RequestForm.objects.filter(rooms__in=rooms_managed)
    total_forms = form_filtered.count()

    num_new_forms = 0
    for form in form_filtered.all():
        if form.requestformstatus_set.filter(manager_id=user.id).count() == 0:
            num_new_forms += 1

    if query:
        if query.get('building'):
            rooms_managed = rooms_managed.filter(building__code__exact=query.get('building'))
        if query.get('floor'):
            rooms_managed = rooms_managed.filter(floor__name__exact=query.get('floor'))
        if query.get('number'):
            rooms_managed = rooms_managed.filter(number__exact=query.get('number'))

    forms = []

    for room in rooms_managed.all():
        for form in room.requestform_set.all():
            form.manager = user
            form.room = room
            form.status = form.requestformstatus_set.filter(room_id=form.room.id, manager_id=user.id)
            if not query or (not query.get('name') and not query.get('status')):
                forms.append(form)
                continue # no filters so add form

            if query.get('status'):
                form_status = form.status.last().status if form.status.count() > 0 else None
                if not validate_status(query.get('status'), form_status):
                    continue   # form status does not match

            if query.get('name'):
                name = query.get('name').lower()
                full_name = f"{form.user.first_name.lower()} {form.user.last_name.lower()}"
                if name not in full_name:
                    continue # name does not match

            forms.append(form)

    forms = sorted(forms, key=lambda x: x.id, reverse=True)
    for i, form in enumerate(forms):
        form.counter = len(forms) - i

    return total_forms, num_new_forms, forms

# Returns true if the status of the form matches the query
# If there is no form status, checks if the query_status is NEW
def validate_status(query_status, form_status):
    if not form_status:
        return query_status == "New"

    if query_status in REV_REQUEST_STATUS_DICT.keys():
        return form_status == REV_REQUEST_STATUS_DICT.get(query_status)

    return False

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


def create_data_from_session(session, key, room=None):
    data = model_to_dict(room) if room else {'building': '', 'floor': '', 'number': '', 'key': False, 'fob': False, 'alarm': False, 'is_active': True}
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
        return ApprovalGroup.objects.prefetch_related('roles__user').get(id=group_id)
    except ApprovalGroup.DoesNotExist:
        return None

def get_all_groups():
    return ApprovalGroup.objects.all()

def get_group_member_ids(group):
    id_arr = group.members.values_list('id', flat=True)
    return [str(user_id) for user_id in id_arr]

def get_group_coordinator_ids(group):
    id_arr = group.coordinators.values_list('id', flat=True)
    return [str(user_id) for user_id in id_arr]

# Checks to see if a group with the same members & coordinators
def get_groups_with_matching_composition(member_ids, coordinator_ids, group_id=None):
    # Normalize and deduplicate member ids (handles strings and duplicates)
    if not member_ids:
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


    group_matches = ApprovalGroup.objects.annotate(
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

