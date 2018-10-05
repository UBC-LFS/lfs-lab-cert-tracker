from django.db import models

class User(models.Model):
    first_name = models.CharField(max_length=256)
    last_name = models.CharField(max_length=256)
    email = models.CharField(max_length=256)
    cwl = models.CharField(max_length=256)

class Cert(models.Model):
    name = models.CharField(max_length=256)

class Lab(models.Model):
    name = models.CharField(max_length=256)

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

    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    cert_id = models.ForeignKey(Cert, on_delete=models.CASCADE)
    cert_path = models.CharField(max_length=256)
    status = models.IntegerField()
    approved_by_user_id = models.IntegerField(null=True)

    completed_date = models.DateField()
    approved_date = models.DateField()
    expiry_date = models.DateField()

class UserLab(models.Model):
    """
    Keeps track of which users belong to which lab
    """
    STUDENT = 0
    PI = 1

    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    lab_id = models.ForeignKey(Lab, on_delete=models.CASCADE)
    role = models.IntegerField()

class LabCert(models.Model):
    """
    Keeps track of what certificate the labs require
    """
    lab_id = models.ForeignKey(Lab, on_delete=models.CASCADE)
    cert_id = models.ForeignKey(Cert, on_delete=models.CASCADE)
