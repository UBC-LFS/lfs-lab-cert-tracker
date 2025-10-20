from django.conf import settings
from django.db.models.functions import Concat
from django.db.models import Q, F, Max, CharField, Value
from urllib.parse import urlparse
from django.forms.models import model_to_dict
from datetime import date
import re
import json
import smtplib
from email.mime.text import MIMEText

from django.contrib.auth.models import User
from app import functions as appFunc
from lfs_lab_cert_tracker.models import Cert
from .models import Building, Floor, Room, RequestForm, RequestFormStatus
from .utils import APPROVED, REV_REQUEST_STATUS_DICT, EMAIL_FOOTER


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
        if room.is_active and room.key:
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
            forms = filter_forms_by_full_name(forms, query.get('name'))
            # forms = forms.filter(Q(user__first_name__icontains=query['name'].strip()) | Q(user__last_name__icontains=query['name'].strip())).distinct()

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


def get_manager_dashboard(user, query=None):
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

def create_data_from_session(session, key, room=None):
    data = model_to_dict(room) if room else {'building': '', 'floor': '', 'number': '', 'key': False, 'fob': False, 'alarm': False, 'is_active': True}
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
        if session[key]['key']:
            data['key'] = session[key]['key']
        if session[key]['fob']:
            data['fob'] = session[key]['fob']
        if session[key]['alarm']:
            data['alarm'] = session[key]['alarm']
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

def count_approved_numbers_by_id_multiple_rooms(status, request_status_forms, manager_id):
    if status != APPROVED:
        return
    manager = User.objects.get(id=manager_id)

    # Tracking info for PI email
    room_info = '<ul>'
    # Structure:
    #   {user_id: {rooms_formatted: [], form: RequestForm, rooms_with_approval_formatted: []}}
    user_details = {}
    users = []

    form = None

    for fs in request_status_forms:
        room = Room.objects.get(id=fs.room_id)
        form = RequestForm.objects.get(id=fs.form_id)
        formatted_room = '<li>{0}</li>'.format(display_room(room))
        user = form.user

        if not user.id in user_details.keys():
            user_details[user.id] = {
                'rooms_formatted': ['<ul>{0}'.format(formatted_room)],
                'form': form,
                'rooms_with_approval_formatted': []
            }
            users.append(user)
        else:
            user_details[user.id]['rooms_formatted'].append(formatted_room)

        if all_managers_approved(form, room):
            approved_rooms = user_details[user.id]['rooms_with_approval_formatted']
            if len(approved_rooms) > 0:
                user_details[user.id]['rooms_with_approval_formatted'].append(formatted_room)
            else:
                user_details[user.id]['rooms_with_approval_formatted'] = ['<ul>{0}'.format(formatted_room)]

    # Send email to applicant if they have approved_rooms
    for user_id in user_details.keys():
        form = user_details[user_id]['form']
        rooms = user_details[user_id]['rooms_with_approval_formatted']
        if len(rooms) > 0:
            rooms.append('</ul>')
            room_info = ''.join(rooms)
            subject, message = get_message(form, form.user, 'user', room_info)
            send(form.user, subject, message)

    # Send email to PI with all rooms
    if len(users) > 1:
        subject, message = get_custom_pi_message_multiple_users(users, user_details, manager)
    elif len(users) > 0:
        rooms = user_details[users[0].id]['rooms_formatted']
        rooms.append('</ul>')
        room_info = ''.join(rooms)
        subject, message = get_message(form, manager, 'pi', room_info)
    else:
        return

    send(manager, subject, message)


def count_approved_numbers_by_id(status, form, room, manager_id):
    if status != APPROVED:
        return

    status_filtered = RequestFormStatus.objects.filter(form_id=form.id, room_id=room.id)
    if not status_filtered.exists():
        return

    # Check if all managers have approved
    all_approved = all_managers_approved(form, room)


    room_info = '<ul><li>{0}</li></ul>'.format(display_room(room))
    if all_approved:
        subject, message = get_message(form, form.user, 'user', room_info)
        send(form.user, subject, message)

    manager = User.objects.get(id=manager_id)
    subject, message = get_message(form, manager, 'pi', room_info)
    send(manager, subject, message)

def all_managers_approved(form, room):
    for i, manager in enumerate(room.managers.all()):
        status_filtered = RequestFormStatus.objects.filter(form_id=form.id, room_id=room.id, manager_id=manager.id)
        if status_filtered.exists():
            latest_status = status_filtered.latest('created_at')

            if latest_status.status != APPROVED:
                return False
        else:
            return False
    return True


def count_approved_numbers(status, form, room):
    if status == APPROVED:
        cache = [0] * room.managers.count()
        for i, manager in enumerate(room.managers.all()):
            status_filtered = RequestFormStatus.objects.filter(form_id=form.id, room_id=room.id, manager_id=manager.id)
            if status_filtered.exists():
                for item in status_filtered:
                    if item.status == APPROVED:
                        cache[i] = 1
                        break
        
        count = 0
        for c in cache:
            count += c
    
        if count >= form.rooms.count():
            send_email(form, room)


def send_email(form, room):

    # Applicant
    subject, message = get_message(form, form.user, 'user')
    send(form.user, subject, message)

    # PI
    room_info = '<ul><li>{0}</li></ul>'.format(display_room(room))
    for manager in room.managers.all():
        subject, message = get_message(form, manager, 'pi', room_info)
        send(manager, subject, message)

def get_custom_pi_message_multiple_users(users, user_room_map, admin):
    user_message = '<div>'
    for i, user in enumerate(users):
        user_rooms = user_room_map[user.id]['rooms_formatted']
        user_rooms.append('</ul>')
        room_info = ''.join(user_rooms)
        user_message+=('''\
        <div>{0}) <b>{1}</b>'s key request for the following room(s):</div>
        {2}
        '''.format(i+1, display_user_first_name(user), room_info))
    user_message+='</div>'

    subject = "Notification: You Have Approved Multiple Users' Key Requests at UBC LFS"
    message = '''\
        <div>
            <p>Hi {0},</p>
            <div>This email is just a notification to inform you that you have approved multiple users' key requests.</div>
            <br>
            {1}
            <div>Please visit <a href={2}>{2}</a> to check the latest status of key requests. Thank you.</div>
            {3}
        </div>
        '''.format(display_user_first_name(admin), user_message, settings.SITE_URL, EMAIL_FOOTER)
    return subject, message

def get_message(form, admin, option, room_info=None):
    subject = ''
    message = ''

    if option == 'user':
        subject = 'Your key request has been approved by UBC LFS'
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>We are delighted to inform you that your key request has been approved for the following room(s):</div>
            {1}
            <div>Please visit <a href={2}>{2}</a> to check the status of your key request. Thank you.</div>
            {3}
        </div>
        '''.format(form.user.get_full_name(), room_info, settings.SITE_URL, EMAIL_FOOTER)
    
    elif option == 'pi':
        subject = "Notification: You Have Approved {0}'s Key Request at UBC LFS".format(display_user_full_name(form.user))
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>This email is just a notification to inform you that you have approved {1}'s key request. Below are the details of the room(s).</div>
            {2}
            <div>Please visit <a href={3}>{3}</a> to check the latest status of key requests. Thank you.</div>
            {4}
        </div>
        '''.format(display_user_first_name(admin), display_user_first_name(form.user), room_info, settings.SITE_URL, EMAIL_FOOTER)
    elif option == 'admin':
        subject = "Notification: {0}'s Key Request Approval at UBC LFS".format(display_user_full_name(form.user))
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>This email is just a notification to inform you that {1}'s key request has been approved. Below are the details of the room.</div>
            {2}
            <div>Please visit <a href={3}>{3}</a> to check the latest status of key requests. Thank you.</div>
            {4}
        </div>
        '''.format(display_user_first_name(admin), display_user_first_name(form.user), room_info, settings.SITE_URL, EMAIL_FOOTER)
    return subject, message


def send(user, subject, message):
    if settings.EMAIL_FROM and appFunc.check_email_valid(user.email):
        sender = settings.EMAIL_FROM
        receiver = '{0} <{1}>'.format(display_user_full_name(user), user.email)

        print(f'An email notification is sent to {receiver}')

        msg = MIMEText(message, 'html')
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = receiver

        try:
            server = smtplib.SMTP(settings.EMAIL_HOST)
            server.sendmail(sender, receiver, msg.as_string())
        except Exception as e:
            print(e)
        finally:
            server.quit()



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


# def count_approved_status(form, room):
#     cache = [0] * room.managers.count()
#     for i, manager in enumerate(room.managers.all()):
#         status_filtered = RequestFormStatus.objects.filter(form_id=form.id, room_id=room.id, manager_id=manager.id)
#         if status_filtered.exists():
#             for item in status_filtered:
#                 if item.status == APPROVED:
#                     cache[i] = 1
#                     break
    
#     count = 0
#     for c in cache:
#         count += c
    
#     return count

