# Generated by Django 2.2 on 2019-06-05 23:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lfs_lab_cert_tracker', '0010_auto_20190605_1610'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usercert',
            name='status',
        ),
    ]
