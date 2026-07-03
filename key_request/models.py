from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User, Group
from lfs_lab_cert_tracker.models import Lab, Cert
from django.db.models import Q, CheckConstraint
from django.core.exceptions import ValidationError

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

    # TODO: Future Extension: Make RoomGroup -> Group; Add a TYPE field (RoomGroup, WorkTagGroup)
    members = models.ManyToManyField(User, related_name='room_groups')
    name = models.TextField(null=False, blank=False, max_length=150)

    class Meta:
        ordering = ['name']
#         TODO: Add a constraint for name, type (one shared name per group type)


class ApprovalGroupCoordinator(models.Model):
    group = models.ForeignKey(ApprovalGroup, null=False, blank=False, on_delete=models.CASCADE)
    user = models.ForeignKey(User, null=False, blank=False, on_delete=models.CASCADE)


    def clean(self):
        if not self.group.members.filter(id=self.user_id).exists():
            raise ValidationError("User must be a member of the group to be assigned as a coordinator.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Room(models.Model):
    building = models.ForeignKey(Building, on_delete=models.DO_NOTHING)
    floor = models.ForeignKey(Floor, on_delete=models.DO_NOTHING)
    number = models.CharField(max_length=100)
    managers = models.ManyToManyField(User)
    groups = models.ManyToManyField(ApprovalGroup, related_name="group_rooms")

    areas = models.ManyToManyField(Lab)
    trainings = models.ManyToManyField(Cert)
    key = models.BooleanField(default=False)
    fob = models.BooleanField(default=False)
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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rooms = models.ManyToManyField(Room)

    role = models.CharField(max_length=100, null=True, blank=True)
    affiliation = models.CharField(max_length=1, choices=AFFILIATIONS, default='3')
    employee_number = models.CharField(max_length=7, null=True, blank=True)
    student_number = models.CharField(max_length=8, null=True, blank=True)
    
    supervisor_first_name = models.CharField(max_length=150)
    supervisor_last_name = models.CharField(max_length=150)
    supervisor_email = models.EmailField(max_length=254)
    
    after_hours_access = models.CharField(max_length=1, choices=AFTER_HOURS_ACCESS, default=None)
    working_alone = models.BooleanField(default=False)
    comment = models.TextField(null=True, blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-id', '-submitted_at']


class RequestFormStatus(models.Model):
    form = models.ForeignKey(RequestForm, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.DO_NOTHING)
    manager = models.ForeignKey(User, blank=True, null=True, on_delete=models.DO_NOTHING, related_name='requestformstatus_manager_set')
    group = models.ForeignKey(ApprovalGroup, blank=True, null=True, on_delete=models.DO_NOTHING, related_name='requestformstatus_group_set')
    operator = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='requestformstatus_operator_set')
    status = models.CharField(max_length=1, choices=REQUEST_STATUS, default=None)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['pk']
        constraints = [
            CheckConstraint(
                check=Q(manager__isnull=False) | Q(group__isnull=False),
                name='manager_or_group_not_null'
            )
        ]
