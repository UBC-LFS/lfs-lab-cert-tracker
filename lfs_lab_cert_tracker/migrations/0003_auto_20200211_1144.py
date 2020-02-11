# Generated by Django 2.2 on 2020-02-11 19:44

import django.core.validators
from django.db import migrations, models
import lfs_lab_cert_tracker.models


class Migration(migrations.Migration):

    dependencies = [
        ('lfs_lab_cert_tracker', '0002_auto_20191024_0840'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usercert',
            name='cert_file',
            field=models.FileField(max_length=256, upload_to=lfs_lab_cert_tracker.models.create_user_cert_disk_path, validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'pdf', 'doc', 'docx']), lfs_lab_cert_tracker.models.FileSizeValidator]),
        ),
    ]
