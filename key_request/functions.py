from django.conf import settings
from django.db.models import Q, F, Max
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
            forms = forms.filter(Q(user__first_name__icontains=query['name'].strip()) | Q(user__last_name__icontains=query['name'].strip())).distinct()

    return forms, total, new_forms


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
        if query['building']:
            rooms_managed = rooms_managed.filter(building__code__exact=query['building'])
        if query['floor']:
            rooms_managed = rooms_managed.filter(floor__name__exact=query['floor'])
        if query['number']:
            rooms_managed = rooms_managed.filter(number__exact=query['number'])

    forms = []
    for room in rooms_managed.all():
        for form in room.requestform_set.all():
            form.manager = user
            form.room = room
            form.status = form.requestformstatus_set.filter(room_id=form.room.id, manager_id=user.id)

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
    for i, form in enumerate(forms):
        form.counter = len(forms) - i

    return total_forms, num_new_forms, forms


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

    # Admin
    # admins = User.objects.filter(is_superuser=True)
    # if admins.count() > 0:
    #     room_info = '<ul>'
    #     for item in RequestFormStatus.objects.filter(form_id=form.id, room_id=room.id):
    #         if item.status == APPROVED:
    #             room_info += '<li>{0} approved by {1}, {2}</li>'.format(display_room(item.room), display_user_full_name(item.operator), convert_date_to_str(item.created_at))
    #     room_info += '</ul>'
                
    #     for admin in admins:
    #         subject, message = get_message(form, admin, 'admin', room_info)
    #         send(admin, subject, message)


def get_message(form, admin, option, room_info=None):
    subject = ''
    message = ''

    if option == 'user':
        subject = 'Your key request has been approved by UBC LFS'
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>We are delighted to inform you that your key request has been approved today. Please visit <a href={1}>{1}</a> to check the status of your key request. Thank you.</div>
            {2}
        </div>
        '''.format(form.user.get_full_name(), settings.SITE_URL, EMAIL_FOOTER)
    
    elif option == 'pi':
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

