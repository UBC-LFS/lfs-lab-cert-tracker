from django import template
from django.contrib.auth.models import User

from key_request import functions as func
from app import functions as appFunc
from key_request.utils import REQUEST_STATUS_DICT, APPROVED, DECLINED, INSUFFICIENT
from key_request.forms import KEY_REQUEST_LABELS
from key_request.models import Room, RequestFormStatus, RequestForm


register = template.Library()


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
    if not form_id:
        return None
    args_splited = args.split(',')
    room_id = args_splited[0]
    manager_id = args_splited[1]
    
    status_filtered = RequestFormStatus.objects.filter(form_id=form_id, room_id=room_id, manager_id=manager_id)
    if status_filtered.exists():
        obj = status_filtered.last()
        return REQUEST_STATUS_DICT[obj.status]
    return None

@register.filter
def get_status_by_group(form_id, args):
    if not form_id:
        return None
    args_splited = args.split(',')
    room_id = args_splited[0]
    group_id = args_splited[1]

    status_filtered = RequestFormStatus.objects.filter(form_id=form_id, room_id=room_id, group_id=group_id).order_by('-created_at')
    if status_filtered.exists():
        obj = status_filtered.first()
        return REQUEST_STATUS_DICT[obj.status]
    return None

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


@register.filter
def join_attribute_with_comma(queryset, attr_name):

    if not queryset:
        return ""

    attr_name, separator = attr_name, ", "

    attr_name = attr_name.strip()
    strings = []

    for obj in queryset:
        val = getattr(obj, attr_name, None)

        if callable(val):
            val = val()

        if val:
            strings.append(str(val))

    return separator.join(strings)