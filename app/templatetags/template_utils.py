from django import template
from app.utils import *

register = template.Library()

@register.filter
def is_user_lab_supervisor(role):
    return True if role == USER_LAB_ROLES['supervisor'] else False