import os
from django.db import models
from django.contrib.auth.models import User as AuthUser
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

"""
Contains app models
"""

class Cert(models.Model):
    name = models.CharField(max_length=256, unique=True)

    def __str__(self):
        return self.name

class Lab(models.Model):
    name = models.CharField(max_length=256, unique=True)

    def __str__(self):
        return self.name

def create_user_cert_disk_path(instance, filename):
    return os.path.join('users', str(instance.user.id), 'certificates', str(instance.cert.id), filename)

class UserCert(models.Model):
    """
    Keeps track of which certs a user has or will need to complete

    All student users should have the default checklist as pending
    as they are created
    """

    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE)
    cert = models.ForeignKey(Cert, on_delete=models.CASCADE)
    cert_file = models.FileField(upload_to=create_user_cert_disk_path)
    uploaded_date = models.DateField(null=True)
    completion_date = models.DateField(null=True)
    expiry_date = models.DateField(null=True)

    class Meta:
        unique_together = (('user', 'cert'))

@receiver(post_delete, sender=UserCert)
def cert_file_delete(sender, instance, **kwargs):
    if instance.cert_file:
        if os.path.isfile(instance.cert_file.path):
            os.remove(instance.cert_file.path)



class UserLab(models.Model):
    """
    Keeps track of which users belong to which lab
    """
    STUDENT = 0
    PRINCIPAL_INVESTIGATOR = 1
    ROLE_CHOICES = [ (STUDENT, "Student"), (PRINCIPAL_INVESTIGATOR, "Principal Investigator") ]
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE)
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    role = models.IntegerField(choices=ROLE_CHOICES)

    class Meta:
        unique_together = (('user', 'lab'))

"""
class SendEmail(models.Model):
    REMIDER_BEFORE_30DAYS = 'remider before 30 days'
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sender')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='receiver')
    purpose = models.CharField(max_length=256)
"""

def send_notification(sender, created, **kwargs):
    if created:
        obj = kwargs['instance']
        print("user: ", obj.user.email)
        print("sender: ", settings.EMAIL_HOST_USER)
        send_mail('Welcome!', 'test', settings.EMAIL_FROM, [ obj.user.email ], fail_silently=False)

post_save.connect(send_notification, sender=UserLab)


class LabCert(models.Model):
    """
    Keeps track of what certificate the labs require
    """
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    cert = models.ForeignKey(Cert, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('lab', 'cert'))
