# Generated by Django 4.2.7 on 2023-12-08 19:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lfs_lab_cert_tracker', '0007_keyrequest_cwl_keyrequest_lfsrole_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='keyrequest',
            name='additional_comments',
            field=models.CharField(default=None),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='keyrequest',
            name='after_hours_access',
            field=models.BooleanField(default=None),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='keyrequest',
            name='requirement_to_proceed',
            field=models.BooleanField(default=None),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='keyrequest',
            name='room_numbers',
            field=models.CharField(default=None, max_length=256),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='keyrequest',
            name='supervisor_email',
            field=models.EmailField(default=None, max_length=254),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='keyrequest',
            name='supervisor_first_name',
            field=models.CharField(default=None, max_length=256),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='keyrequest',
            name='supervisor_last_name',
            field=models.CharField(default=None, max_length=256),
            preserve_default=False,
        ),
    ]
