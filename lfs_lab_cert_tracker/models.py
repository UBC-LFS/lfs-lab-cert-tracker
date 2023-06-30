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
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _


class Lab(models.Model):
    """ Lab Model """

    name = models.CharField(max_length=256, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Cert(models.Model):
    """ Certificate Model """

    name = models.CharField(max_length=256, unique=True)
    expiry_in_years = models.IntegerField(default=0)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

def create_user_cert_disk_path(instance, filename):
    return os.path.join('users', str(instance.user.id), 'certificates', str(instance.cert.id), filename)

def format_bytes(size):
    power = 2**10
    n = 0
    power_labels = {0 : '', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size > power:
        size /= power
        n += 1
    return str( round(size, 2) ) + ' ' + power_labels[n]

def FileSizeValidator(file):
    if int(file.size) > int(settings.MAX_UPLOAD_SIZE):
        raise ValidationError(
            _('The maximum file size that can be uploaded is 1.5 MB. The size of this file (%(name)s) is %(size)s '), params={'name': file.name, 'size': format_bytes(int(file.size)) }, code='file_size_limit'
        )

class UserApiCerts(models.Model):
    """
    The Certificates for a user retrieved from the WPL api
    Issues with API:
    - Only gets the first 10 certificates
    - Server timeouts on users
    - Some certificates don't show up for users
    """

    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE)
    training_name = models.CharField(max_length=256)
    completion_date = models.DateField()
    
class UserCert(models.Model):
    """
    Keeps track of which certs a user has or will need to complete

    All student users should have the default checklist as pending
    as they are created
    """

    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE)
    cert = models.ForeignKey(Cert, on_delete=models.CASCADE)
    cert_file = models.FileField(
        max_length=256,
        upload_to=create_user_cert_disk_path,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'pdf', 'doc', 'docx']),
            FileSizeValidator
        ]
    )
    uploaded_date = models.DateField()
    completion_date = models.DateField()
    expiry_date = models.DateField()

    class Meta:
        unique_together = (('user', 'cert'))

    def save(self, *args, **kwargs):
        """ Reduce a size and quality of the image """
        if not self.cert_file:
            return super(UserCert, self).save(*args, **kwargs)
        file_split = os.path.splitext(self.cert_file.name)
        file_name = file_split[0]
        file_extension = file_split[1]

        if self.cert_file and file_extension.lower() in ['.jpg', '.jpeg', '.png']:
            img = PILImage.open( self.cert_file )

            if img.mode == 'P':
                img = img.convert('RGB')

            if img.mode in ['RGBA']:
                background = PILImage.new( img.mode[:-1], img.size, (255,255,255) )
                background.paste(img, img.split()[-1])
                img = background

            # Check image's width and height
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
            img.save(output, format='JPEG', quality=70) # Reduce a quality by 70%
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
    ROLE_CHOICES = [ (LAB_USER, "User"), (PRINCIPAL_INVESTIGATOR, "Supervisor") ]
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE)
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    role = models.IntegerField(choices=ROLE_CHOICES)

    class Meta:
        unique_together = (('user', 'lab'))
        ordering = ['user']


# Send an email when adding a user to a lab
def send_notification(sender, created, **kwargs):
    if created:
        obj = kwargs['instance']
        title = 'You are added to {0} in LFS TRMS'.format(obj.lab.name)
        message = '''\
        <div>
            <p>Hi {0} {1},</p>
            <div>You have recently been added to {2} in the LFS Training Record Management System. Please visit <a href={3}>{3}</a> to upload your training records. Thank you.</div>
            <br />
            <div>
                <b>Please note that if you try to access the LFS Training Record Management System off campus,
                you must be connected via
                <a href="https://it.ubc.ca/services/email-voice-internet/myvpn">UBC VPN</a>.</b>
            </div>
            <br />
            <p>Best regards,</p>
            <p>LFS Training Record Management System</p>
        </div>
        '''.format(
            obj.user.first_name,
            obj.user.last_name,
            obj.lab.name,
            settings.SITE_URL
        )

        valid_email = False
        try:
            validate_email(obj.user.email)
            valid_email = True
        except ValidationError as e:
            print(e)

        if valid_email:
            send_mail(title, message, settings.EMAIL_FROM, [ obj.user.email ], fail_silently=False, html_message=message)


post_save.connect(send_notification, sender=UserLab)


class LabCert(models.Model):
    """
    Keeps track of what certificate the labs require
    """
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    cert = models.ForeignKey(Cert, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('lab', 'cert'))
        #ordering = ['cert']

    def __str__(self):
        return self.cert.name

class UserInactive(models.Model):
    """ Update date when a user become inactive """

    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE)
    inactive_date = models.DateField(null=True)
