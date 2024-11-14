from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from lfs_lab_cert_tracker.models import Lab, Cert
from .utils import *


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


class Room(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE)
    number = models.CharField(max_length=10)
    managers = models.ManyToManyField(User)
    areas = models.ManyToManyField(Lab)
    trainings = models.ManyToManyField(Cert)
    slug = models.SlugField(max_length=256, unique=True)
    created_on = models.DateField(auto_now_add=True)
    updated_on = models.DateField(auto_now=True)

    class Meta:
        unique_together = ['building', 'floor', 'number']
        ordering = ['building', 'floor', 'number']

    def __str__(self):
        return self.number
    
    def save(self, *args, **kwargs):
        self.slug = slugify(self.building.code + ' ' + self.floor.name + ' ' + self.number)
        super(Room, self).save(*args, **kwargs)


class RequestForm(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rooms = models.ManyToManyField(Room)

    role = models.CharField(max_length=100, null=True, blank=True)
    affliation = models.CharField(max_length=1, choices=AFFLIATIONS, default='3')
    employee_number = models.CharField(max_length=7, null=True, blank=True)
    student_number = models.CharField(max_length=8, null=True, blank=True)
    
    supervisor_first_name = models.CharField(max_length=150)
    supervisor_last_name = models.CharField(max_length=150)
    supervisor_email = models.EmailField(max_length=254)
    
    after_hours_access = models.CharField(max_length=1, choices=AFTER_HOUR_ACCESS, default=None)
    working_alone = models.BooleanField(default=False)
    comment = models.TextField(null=True, blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-id', '-submitted_at']


class RequestFormStatus(models.Model):
    form = models.ForeignKey(RequestForm, on_delete=models.CASCADE)
    room_id = models.BigIntegerField()
    manager_id = models.BigIntegerField()
    operator_id = models.BigIntegerField()
    status = models.CharField(max_length=1, choices=REQUEST_STATUS, default=None)
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['pk']


    # def get_fields(self):
    #     fields = []

    #     renamed_fields = {
    #         'role': 'Applicant Role in LFS',
    #         'affliation': 'Applicant UBC Affliation',
    #         'supervisor_first_name': "Supervisor's First Name",
    #         'supervisor_last_name': "Supervisor's Last Name",
    #         'supervisor_email': "Supervisor's Email",
    #         'after_hours_access': 'After hours access',
    #         'working_alone': 'Working alone and/or in isolation',
    #         'room_numbers': 'Room Numbers that I need access to',
    #         'comment': 'Additional Comments'
    #     }

    #     choices_fields = ['affliation', 'after_hours_access', 'building_name']

    #     for field in self._meta.fields:
    #         if field.name == 'id' or field.name == 'user' or field.name == 'lab':
    #             continue

    #         name = []
    #         val = getattr(self, field.name)

    #         if field.name in renamed_fields.keys():
    #             name.append(renamed_fields[field.name])
    #         else:
    #             name = [sp.capitalize() for sp in field.name.split('_')]
            
    #         if field.name in choices_fields:
    #             val = getattr(self, 'get_{0}_display'.format(field.name))()

    #         fields.append( (' '.join(name), val) )
    #     return fields