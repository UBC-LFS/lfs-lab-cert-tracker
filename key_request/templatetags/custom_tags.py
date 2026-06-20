from django import template
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

from key_request import functions as func
from app import functions as appFunc
from key_request.utils import REQUEST_STATUS_DICT
from key_request.forms import KEY_REQUEST_LABELS
from key_request.models import Room, RequestFormStatus, RequestForm

from django.template.defaultfilters import pluralize
from datetime import date


register = template.Library()


@register.filter
def get_user(username):
    user = get_object_or_404(User, username=username)
    return user.get_full_name()


@register.filter
def get_fields(obj, arg=None):
    exclude = ['id', 'user', 'updated_at']
    choices_fields = ['affiliation', 'after_hours_access']

    fields = []
    for field in obj._meta.fields:
        if field.name not in exclude:
            value = getattr(obj, field.name)
            if field.name in choices_fields:
                value = getattr(obj, 'get_{0}_display'.format(field.name))()
            fields.append( (make_field_name_label(field), value) )
    return fields


def make_field_name_label(field):
    if field.name in KEY_REQUEST_LABELS:
        return KEY_REQUEST_LABELS[field.name]
    
    name_list = [sp.capitalize() for sp in field.name.split('_')]
    return ' '.join(name_list)


@register.simple_tag
def get_help_text_by_field(fields, field_name):
    for f in fields:
        if f.label == field_name:
            return f.help_text
    return None


@register.filter
def get_status_display(status):
    if status and status in REQUEST_STATUS_DICT.keys():
        return REQUEST_STATUS_DICT[status]


@register.filter
def get_user_name(user):
    if user:
        return appFunc.get_user_name(user)


@register.filter
def get_user_full_name(user_id):
    if user_id:
        user = User.objects.get(id=user_id)
        return appFunc.get_user_name(user)


@register.filter
def get_room(room_id):
    if room_id:
        return Room.objects.get(id=room_id)


@register.filter
def get_status_by_manager(form_id, args):
    args_splited = args.split(',')
    room_id = args_splited[0]
    manager_id = args_splited[1]
    
    status_filtered = RequestFormStatus.objects.filter(form_id=form_id, room_id=room_id, manager_id=manager_id)
    if status_filtered.exists():
        obj = status_filtered.last()
        return REQUEST_STATUS_DICT[obj.status]
    return None


@register.filter
def date_to_str(d):
    if d:
        return func.convert_date_to_str(d)


@register.filter
def remaining_days(d):
    if d:
        duration = d - date.today()
        suffix = pluralize(duration.days)
        return '<strong>{0}</strong> day{1} left'.format(duration.days, suffix)


@register.simple_tag
def get_status_by_room_and_form(form_id, room_id):
    if not form_id or not room_id:
        return False
    try:
        form = RequestForm.objects.get(id=form_id)
        room = Room.objects.get(id=room_id)
    except (RequestForm.DoesNotExist, Room.DoesNotExist):
        return False

    return func.all_pis_approved(form, room)



@register.simple_tag
def concat_strings(*args):
    s = ''
    for a in args: 
        s += str(a) + ','
    return s


@register.simple_tag
def concat_strings_dash(*args):
    s = ''
    for i, a in enumerate(args): 
        s += str(a)
        if i < len(args) - 1:
            s += '-'
    return s


@register.filter
def display_room(room, args=None):
    return func.display_room(room, args)