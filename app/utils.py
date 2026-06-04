from django.db.models import IntegerChoices


NUM_PER_PAGE = 20

class Role(IntegerChoices):
    USER = 0, 'User'
    PI = 1, 'PI'
    ADMIN = 2, 'Admin'