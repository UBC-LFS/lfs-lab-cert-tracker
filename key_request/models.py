from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User, Group
from lfs_lab_cert_tracker.models import Lab, Cert
from django.db.models import Q, CheckConstraint

from datetime import datetime

from .utils import AFFILIATIONS, AFTER_HOURS_ACCESS, REQUEST_STATUS


class Building(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    slug = models.SlugField(max_length=20, unique=True)
    created_on = models.DateField(auto_now_add=True)
    updated_on = models.DateField(auto_now=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return '{0} ({1})'.format(self.name, self.code)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.code)
        super(Building, self).save(*args, **kwargs)


class Floor(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    created_on = models.DateField(auto_now_add=True)
    updated_on = models.DateField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Floor, self).save(*args, **kwargs)

class ApprovalGroup(models.Model):
    """ Represents a group of users associated with a room. """

    name = models.TextField(null=False, blank=False, max_length=150)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    @property
    def user_roles_ordered(self):
        return self.roles.all().order_by('-role', 'user__first_name', 'user__last_name')

    @property
    def members(self):
        return User.objects.filter(approval_group_roles__group=self)

    @property
    def coordinators(self):
        return User.objects.filter(
            approval_group_roles__group=self,
            approval_group_roles__role=ApprovalGroupRole.Role.COORDINATOR,
        )


class ApprovalGroupRole(models.Model):
    class Role(models.IntegerChoices):
        MEMBER = 1, 'Member'
        COORDINATOR = 2, 'Coordinator'

    group = models.ForeignKey(ApprovalGroup, on_delete=models.CASCADE, related_name='roles')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approval_group_roles')
    role = models.IntegerField(choices=Role.choices, default=Role.MEMBER)

    class Meta:
        unique_together = ('group', 'user')

# TODO Change managers to be supervisors
class Room(models.Model):
    building = models.ForeignKey(Building, on_delete=models.DO_NOTHING)
    floor = models.ForeignKey(Floor, on_delete=models.DO_NOTHING)
    number = models.CharField(max_length=100)
    managers = models.ManyToManyField(User)
    groups = models.ManyToManyField(ApprovalGroup, related_name="group_rooms")

    areas = models.ManyToManyField(Lab)
    trainings = models.ManyToManyField(Cert)
    key = models.BooleanField(default=False)
    card_access = models.BooleanField(default=False)
    alarm = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    note = models.TextField(null=True, blank=True)

    slug = models.SlugField(max_length=256, unique=True)
    created_on = models.DateField(auto_now_add=True)
    updated_on = models.DateField(auto_now=True)

    class Meta:
        ordering = ['building', 'floor', 'number']

    def __str__(self):
        return self.number
    
    def save(self, *args, **kwargs):
        self.slug = slugify(self.building.code + ' ' + self.floor.name + ' ' + self.number + ' ' + str(datetime.now().timestamp()))
        super(Room, self).save(*args, **kwargs)


class RequestForm(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='request_forms')
    rooms = models.ManyToManyField(Room)

    role = models.CharField(max_length=100, null=True, blank=True)
    affiliation = models.CharField(max_length=1, choices=AFFILIATIONS, default='3')
    employee_number = models.CharField(max_length=7, null=True, blank=True)
    student_number = models.CharField(max_length=8, null=True, blank=True)
    
    supervisor = models.ForeignKey(User,  on_delete=models.SET_NULL, null=True, related_name='supervised_request_forms')
    expiry_date = models.DateField(null=True, blank=True)

    after_hours_access = models.CharField(max_length=1, choices=AFTER_HOURS_ACCESS, default=None)
    working_alone = models.BooleanField(default=False)
    comment = models.TextField(null=True, blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-pk', '-submitted_at']

# TODO Change manager to be supervisor; also change the related name
class RequestFormStatus(models.Model):

    class SupervisorType(models.IntegerChoices):
        ROOM = 1, 'Room'
        REQUEST = 2, 'Request'


    form = models.ForeignKey(RequestForm, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.DO_NOTHING)
    manager = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, related_name='requestformstatus_manager_set')
    supervisor_type = models.IntegerField(choices=SupervisorType.choices, default=None, null=True, blank=True)

    group = models.ForeignKey(ApprovalGroup, blank=True, null=True, on_delete=models.SET_NULL, related_name='requestformstatus_group_set')
    operator = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, related_name='requestformstatus_operator_set')
    status = models.CharField(max_length=1, choices=REQUEST_STATUS, default=None)
    created_at = models.DateTimeField(auto_now_add=True)


class RoomEmail(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    type = models.CharField(max_length=20)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-pk']


class UserFilter(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    json = models.JSONField()