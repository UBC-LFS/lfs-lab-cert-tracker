import os
from django.db import models

class User(models.Model):
    first_name = models.CharField(max_length=256)
    last_name = models.CharField(max_length=256)
    email = models.CharField(max_length=256)
    cwl = models.CharField(max_length=256, unique=True)

    def __str__(self):
        return self.cwl

class Cert(models.Model):
    name = models.CharField(max_length=256, unique=True)

    def __str__(self):
        return self.name

class Lab(models.Model):
    name = models.CharField(max_length=256, unique=True)

    def __str__(self):
        return self.name

def create_user_cert_disk_path(instance, filename):
    return os.path.join('users', str(instance.user.id), 'certificates', str(instance.cert.id))

class UserCert(models.Model):
    """
    Keeps track of which certs a user has or will need to complete

    All student users should have the default checklist as pending
    as they are created
    """
    PENDING = 0
    APPROVED = 1
    INVALID = 2
    EXPIRED = 3

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cert = models.ForeignKey(Cert, on_delete=models.CASCADE)

    cert_file = models.FileField(upload_to=create_user_cert_disk_path)

    status = models.IntegerField()
    approved_by_user_id = models.IntegerField(null=True)

    uploaded_date = models.DateField(null=True)
    approved_date = models.DateField(null=True)
    expiry_date = models.DateField(null=True)

    class Meta:
        unique_together = (('user', 'cert'))

class UserLab(models.Model):
    """
    Keeps track of which users belong to which lab
    """
    STUDENT = 0
    PI = 1

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    role = models.IntegerField()

    class Meta:
        unique_together = (('user', 'lab'))

class LabCert(models.Model):
    """
    Keeps track of what certificate the labs require
    """
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    cert = models.ForeignKey(Cert, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('lab', 'cert'))
