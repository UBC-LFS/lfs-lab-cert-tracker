from django.conf import settings
from django.db.models.functions import Concat
from django.db.models import Q, F, Max, CharField, Value, OuterRef, Exists, Subquery
from urllib.parse import urlparse
from django.forms.models import model_to_dict
from datetime import date
import re
import json
import smtplib
from email.mime.text import MIMEText

from django.contrib.auth.models import User
from app import functions as appFunc
from app.utils import UserRole
from lfs_lab_cert_tracker.models import Cert, UserLab
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

# ============== MANAGER/ADMIN =====================

def get_rooms_managed(user):
    """ Get all rooms in which the user has a role of PI or PI proxy of areas associated with a room """

    areas = (user.userlab_set.all()
             .filter(role__in=[UserRole.PI_PROXY, UserRole.PRINCIPAL_INVESTIGATOR])
             .values_list('lab_id', flat=True)
             .distinct())

    return Room.objects.filter(areas__in=areas).distinct()

def get_manager_dashboard(user, query=None):

    # SET-UP
    rooms_managed = get_rooms_managed(user)
    form_filtered = RequestForm.objects.filter(rooms__in=rooms_managed).distinct()


    # PART 1: Stats
    total_forms = form_filtered.count()

    num_new_forms = form_filtered.exclude(
        requestformstatus__manager=user
    ).count()


    # PART 2: Filtering
    # a) Filter the rooms
    if query:
        if query.get('building'):
            rooms_managed = rooms_managed.filter(building__code__exact=query.get('building'))
        if query.get('floor'):
            rooms_managed = rooms_managed.filter(floor__name__exact=query.get('floor'))
        if query.get('number'):
            rooms_managed = rooms_managed.filter(number__exact=query.get('number'))

    # b) Filter the forms
    forms = []

    rooms_managed = rooms_managed.prefetch_related(
        'requestform_set__requestformstatus_set',
        'requestform_set__user',
    )

    apply_form_filters = query and (query.get('name') or query.get('status'))

    for room in rooms_managed:

        form_qs = room.requestform_set.all()

        if apply_form_filters:
            if name := query.get('name'):
                form_qs = form_qs.filter(
                    Q(user__first_name__icontains=name) |
                    Q(user__last_name__icontains=name)
                )
            if query_status := query.get('status'):
                # handle the case that status is New (therefore there is no requestformstatus for that user)
                status_history_ordered = RequestFormStatus.objects.filter(
                    form_id=OuterRef('pk'),
                    room_id=room.id,
                    manager_id=user.id
                ).order_by('-created_at')

                if query_status == "New":
                    form_qs = form_qs.filter(~Exists(status_history_ordered))
                else:
                    status = REV_REQUEST_STATUS_DICT.get(query_status)

                    latest_status = status_history_ordered.values('status')[:1]

                    form_qs = form_qs.annotate(
                        latest_status=Subquery(latest_status)
                    ).filter(
                        latest_status = status
                    )

        for form in form_qs:

            form.manager = user
            form.room = room

            statuses = form.requestformstatus_set.filter(room_id=room.id, manager_id=user.id)
            current_status = statuses.order_by('-created_at').first()
            form.status = statuses
            form.current_status = current_status

            forms.append(form)


    forms.sort(key=lambda x: x.id, reverse=True)
    for i, form in enumerate(forms, 1):
        form.counter = i

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

        if len(session[key]['areas']) > 0:
            area_ids = session[key]['areas']

        if len(session[key]['trainings']) > 0:
            training_ids = session[key]['trainings']

    return data, area_ids, training_ids

def update_data_from_post_and_session(post, session, key, tab, room=None):
    data, area_ids, training_ids = create_data_from_session(session, key, room)
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

    elif tab == 'areas':
        areas = str_to_int(post.getlist('areas[]'))
        if not is_two_lists_equal(area_ids, areas):
            area_ids = areas

    elif tab == 'trainings':
        trainings = str_to_int(post.getlist('trainings[]'))
        if not is_two_lists_equal(training_ids, trainings):
            training_ids = trainings

    return data, area_ids, training_ids

# SENDING EMAIL NOTIFICATIONS

# Sends email to manager (admin OR pi) approving the request, and optionally sends to user if KR has full approval
def count_approved_numbers_by_id(status, form, room, manager_id, absent_pi=None):
    if status != APPROVED:
        return

    status_filtered = RequestFormStatus.objects.filter(form_id=form.id, room_id=room.id)
    if not status_filtered.exists():
        return

    # Check if all PIs have approved
    all_approved = all_pis_approved(form, room)

    room_info = '<ul><li>{0}</li></ul>'.format(display_room(room))
    if all_approved:
        subject, message = get_message(form.user, form.user, 'user', room_info)
        send(form.user, subject, message)

    manager = User.objects.get(id=manager_id)

    if absent_pi:
        pi = User.objects.get(id=absent_pi)
        subject, message = get_message(form.user, pi, 'absent_pi', room_info, manager)
        send(pi, subject, message)
        subject, message = get_message(form.user, pi, 'admin', room_info, manager)
        send(manager, subject, message)
    else:
        subject, message = get_message(form.user, manager, 'pi', room_info)
        send(manager, subject, message)

# Count approval numbers for "Update All";
# Manager_id is the id of the operator (the approving user)
# pi_room_map includes all rooms associated with each PI
#   CASE 1: If the pi_room_map has a size == 1 (a single PI) AND the pi_id matches the manager_id -> the user is approving their own requests
#   CASE 2: If the pi_room_map has a size > 1 OR the pi_id does NOT match the manager_id -> the user is approving on behalf of another PI
#           note that this will only ever be for a single user

def count_approved_numbers_by_id_multiple_rooms(status, request_status_forms, manager_id, pi_room_map):
    if status != APPROVED:
        return

    manager = User.objects.get(id=manager_id)

    # get the list of users and the rooms associated with them
    user_details = process_request_forms(request_status_forms)
    users = [details['user'] for details in user_details.values()]

    send_list = []

    # Get email message for applicants that have approved_rooms
    for details in user_details.values():
        rooms = details.get('rooms_with_approval_formatted', [])
        if rooms:
            room_info = '<ul>' + ''.join(rooms) + '</ul>'
            subject, message = get_message(details['user'], details['user'], 'user', room_info)
            send_list.append(make_send_obj(details['user'], subject, message))


    if approving_on_behalf_of_pis(pi_room_map, manager_id):
        #admin message
        prepare_admin_message(pi_room_map, manager_id, users[0], manager, send_list)
    else:
        # pi message
        prepare_pi_message(users, user_details, manager, send_list)

    # Bulk send emails
    if send_list:
        print(f"Sending {len(send_list)} message(s)")
        send_multiple(send_list)


def approving_on_behalf_of_pis(pi_room_map, id):
    if len(pi_room_map) > 1:
        return True
    first_key = next(iter(pi_room_map.keys()))
    return int(first_key) != int(id)

def prepare_pi_message(users, user_details, manager, send_list):
    if len(users) > 1:
        subject, message = get_custom_pi_message_multiple_users(users, user_details, manager)
        send_list.append(make_send_obj(manager, subject, message))
    elif len(users) > 0:
        first_details = user_details[users[0].id]
        rooms = first_details.get('rooms_formatted', [])
        user = first_details['user']

        room_info = '<ul>' + ''.join(rooms) + '</ul>'
        subject, message = get_message(user, manager, 'pi', room_info)
        send_list.append(make_send_obj(manager, subject, message))

def prepare_admin_message(pi_room_map, manager_id, user, manager, send_list):
    pi_list = []

    for pi_id, room_ids in pi_room_map.items():
        rooms = []
        for room_id in room_ids:
            rooms.append('<li>{0}</li>'.format(display_room(Room.objects.get(id=room_id))))
        room_info =  '<ul>' + ''.join(rooms) + '</ul>'
        pi_room_map[pi_id] = rooms

        if int(pi_id) != int(manager_id):
            pi = User.objects.get(id=pi_id)
            pi_list.append(pi)
            subject, message = get_message(user, pi, 'absent_pi', room_info, manager)
            send_obj = make_send_obj(pi, subject, message)
            send_list.append(send_obj)

    subject, message = get_custom_admin_message_multiple_pis(pi_list, pi_room_map, user, manager)
    send_list.append(make_send_obj(manager, subject, message))

# Processes the request_status_forms where each user is associated with a formatted room (list)
# and rooms that have full approval (e.g. all PIs have approved)
# Structure:{ user_id: { user: User, room_ids: [], rooms_formatted: [], rooms_with_approval_formatted: []}}
def process_request_forms(request_status_forms):
    user_details = {}
    for fs in request_status_forms:
        room = Room.objects.get(id=fs.room_id)
        form = RequestForm.objects.get(id=fs.form_id)
        formatted_room = '<li>{0}</li>'.format(display_room(room))
        user = form.user

        if user.id not in user_details.keys():
            user_details[user.id] = {
                'user': user,
                'room_ids': [fs.room_id],
                'rooms_formatted': [formatted_room],
                'rooms_with_approval_formatted': []
            }
        else:
            detail = user_details[user.id]
            if fs.room_id not in detail['room_ids']:
                detail['rooms_formatted'].append(formatted_room)
                detail['room_ids'].append(fs.room_id)

        detail = user_details[user.id]
        if all_pis_approved(form, room):
            approved_rooms = detail['rooms_with_approval_formatted']
            if formatted_room not in approved_rooms:
                approved_rooms.append(formatted_room)

    return user_details

def make_send_obj(user, subject, message):
    return {
        'user': user,
        'subject': subject,
        'message': message
    }

# Returns True if all PIs have approved a room
def all_pis_approved(form, room):
    # Check if there are no managers associated in a room
    if len(room.managers.all()) == 0:
        return False

    for i, manager in enumerate(room.managers.all()):
        status_filtered = RequestFormStatus.objects.filter(form_id=form.id, room_id=room.id, manager_id=manager.id)
        if status_filtered.exists():
            latest_status = status_filtered.latest('created_at')
            if latest_status.status != APPROVED:
                return False
        else:
            return False
    return True

def get_custom_admin_message_multiple_pis(pis, pi_room_map, user, admin):

    admin_id = str(admin.id)
    if pi_room_map.get(admin_id, None):
        admin_rooms = pi_room_map.get(admin_id)
        room_info = '<ul>' + ''.join(admin_rooms) + '</ul>'
    else:
        room_info = '<br>'

    message = '''\
            <div>
                <p>Hi {0},</p>
                <div>This email is just a notification to inform you that you have approved {1}'s key request(s).</div>
                {2}
            '''.format(display_user_first_name(admin), display_user_first_name(user), room_info)

    if not pis:
        pi_message = ''
    else:
        msg = '<ol>'
        for i, pi in enumerate(pis):
            pi_id = str(pi.id)
            pi_rooms = pi_room_map.get(pi_id, None)
            room_info = '<ul>' + ''.join(pi_rooms) + '</ul>'

            msg+=('''\
                <li><b>{0}</b>:</li>
                {1}
            '''.format(display_user_first_name(pi), room_info))
        msg += '</ol>'
        pi_message = '''\
            <div> You have approved {0}'s key request(s) on behalf of the following PIs:</div>
            {1}
        '''.format(display_user_first_name(user), msg)

    subject = f"Notification: You Have Approved Multiple Key Requests at UBC LFS"

    message += '''\
            {0}
            <div>Please visit <a href={1}>{1}</a> to check the latest status of key requests. Thank you.</div>
            {2}
        </div>
        '''.format(pi_message, settings.SITE_URL, EMAIL_FOOTER)
    return subject, message

def get_custom_pi_message_multiple_users(users, user_room_map, manager):
    user_message = '<div>'
    for i, user in enumerate(users):
        user_rooms = user_room_map[user.id]['rooms_formatted']
        room_info = '<ul>' + ''.join(user_rooms) + '</ul>'
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
        '''.format(display_user_first_name(manager), user_message, settings.SITE_URL, EMAIL_FOOTER)
    return subject, message

def get_message(user, pi, option, room_info=None, admin=None):
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
        '''.format(user.get_full_name(), room_info, settings.SITE_URL, EMAIL_FOOTER)
    
    elif option == 'pi':
        subject = "Notification: You Have Approved {0}'s Key Request at UBC LFS".format(display_user_full_name(user))
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>This email is just a notification to inform you that you have approved {1}'s key request. Below are the details of the room(s).</div>
            {2}
            <div>Please visit <a href={3}>{3}</a> to check the latest status of key requests. Thank you.</div>
            {4}
        </div>
        '''.format(display_user_first_name(pi), display_user_first_name(user), room_info, settings.SITE_URL, EMAIL_FOOTER)
    elif option == 'admin':
        subject = "Notification: {0}'s Key Request Approval at UBC LFS".format(display_user_full_name(user))
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>This email is just a notification to inform you that {1}'s key request has been approved on behalf of {2}. Below are the details of the room.</div>
            {3}
            <div>Please visit <a href={4}>{4}</a> to check the latest status of key requests. Thank you.</div>
            {5}
        </div>
        '''.format(display_user_first_name(admin), display_user_first_name(user), display_user_first_name(pi), room_info, settings.SITE_URL, EMAIL_FOOTER)
    elif option == 'absent_pi':
        subject = "Notification: {0}'s Key Request Approval at UBC LFS".format(display_user_full_name(user))
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>This email is just a notification to inform you that {1} has approved {2}'s key request for a room. Below are the details of the room(s).</div>
            {3}
            <div>Please visit <a href={4}>{4}</a> to check the latest status of key requests. Thank you.</div>
            {5}
        </div>
        '''.format(display_user_first_name(pi), display_user_first_name(admin), display_user_first_name(user), room_info, settings.SITE_URL, EMAIL_FOOTER)
    return subject, message

def send_email(form, room):

    # Applicant
    subject, message = get_message(form.user, form.user, 'user')
    send(form.user, subject, message)

    # PI
    room_info = '<ul><li>{0}</li></ul>'.format(display_room(room))
    for manager in room.managers.all():
        subject, message = get_message(form.user, manager, 'pi', room_info)
        send(manager, subject, message)

def send_multiple(contents):
    try:
        server = smtplib.SMTP(settings.EMAIL_HOST)
        for item in contents:
            user = item['user']
            subject = item['subject']
            message = item['message']
            if settings.EMAIL_FROM and appFunc.check_email_valid(user.email):
                sender = settings.EMAIL_FROM
                receiver = '{0} <{1}>'.format(display_user_full_name(user), user.email)

                print(f'An email notification is sent to {receiver}')

                msg = MIMEText(message, 'html')
                msg['Subject'] = subject
                msg['From'] = sender
                msg['To'] = receiver
                server.sendmail(sender, receiver, msg.as_string())
    except Exception as e:
        print(e)
    finally:
        server.quit()

def send(user, subject, message):
    if settings.EMAIL_FROM and appFunc.check_email_valid(user.email):
        sender = settings.EMAIL_FROM
        receiver = '{0} <{1}>'.format(display_user_full_name(user), user.email)

        print(f'SEND: An email notification is sent to {receiver}')

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
        'areas': url + 'areas&next=' + next,
        'trainings': url + 'trainings&next=' + next
    }


def convert_date_to_str(date):
    return date.strftime('%Y-%m-%d')
