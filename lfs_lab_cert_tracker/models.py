import os
from django.db import models
from django.contrib.auth.models import User as AuthUser
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from io import BytesIO
import sys
from PIL import Image as PILImage
from django.core.files.uploadedfile import InMemoryUploadedFile


"""
Contains app models
"""

class Cert(models.Model):
    name = models.CharField(max_length=256, unique=True)
    expiry_in_years = models.IntegerField(default=0)

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
    uploaded_date = models.DateField()
    completion_date = models.DateField()
    expiry_date = models.DateField()

    class Meta:
        unique_together = (('user', 'cert'))

    def save(self, *args, **kwargs):
        """ Reduce a size and quality of the image """

        file_split = os.path.splitext(self.cert_file.name)
        file_name = file_split[0]
        file_extension = file_split[1]
        if self.cert_file and file_extension.lower() in ['.jpg', '.jpeg', '.png']:
            img = PILImage.open( self.cert_file )
            if img.mode in ['RGBA']:
                background = PILImage.new( img.mode[:-1], img.size, (255,255,255) )
                background.paste(img, img.split()[-1])
                img = background

            width, height = img.size
            if width > 4000 or height > 3000:
                width, height = width/3.0, height/3.0
            elif width > 3000 or height > 2000:
                width, height = width/2.5, height/2.5
            elif width > 2000 or height > 1000:
                width, height = width/2.0, height/2.0
            elif width > 1000 or height > 500:
                width, height = width/1.5, height/1.5

            img.thumbnail( (width, height), PILImage.ANTIALIAS )
            output = BytesIO()
            img.save(output, format='JPEG', quality=70)
            output.seek(0)
            self.cert_file = InMemoryUploadedFile(output,'ImageField', "%s.jpg" % file_name, 'image/jpeg', sys.getsizeof(output), None)
        super(UserCert, self).save(*args, **kwargs)

@receiver(post_delete, sender=UserCert)
def cert_file_delete(sender, instance, **kwargs):
    if instance.cert_file:
        if os.path.isfile(instance.cert_file.path):
            os.remove(instance.cert_file.path)

class UserLab(models.Model):
    """
    Keeps track of which users belong to which lab
    """
    LAB_USER = 0
    PRINCIPAL_INVESTIGATOR = 1
    ROLE_CHOICES = [ (LAB_USER, "Lab User"), (PRINCIPAL_INVESTIGATOR, "Principal Investigator") ]
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE)
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    role = models.IntegerField(choices=ROLE_CHOICES)

    class Meta:
        unique_together = (('user', 'lab'))


def send_notification(sender, created, **kwargs):
    if created:
        obj = kwargs['instance']
        title = 'You are added to a lab'
        message = """
            Hi there,
            
            You are recently added to a lab in the LFS Lab Cert Tracker. Please visit and check your certificates.
            {0}

            Thank you.

            LFS Lab Cert Tracker
        """.format( os.environ['LFS_LAB_CERT_TRACKER_URL'] )
        send_mail(title, message, settings.EMAIL_FROM, [ obj.user.email ], fail_silently=False)

post_save.connect(send_notification, sender=UserLab)


class LabCert(models.Model):
    """
    Keeps track of what certificate the labs require
    """
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    cert = models.ForeignKey(Cert, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('lab', 'cert'))

class UserInactive(models.Model):
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE)
    inactive_date = models.DateField(null=True)
