# Generated by Django 2.2 on 2019-06-07 20:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lfs_lab_cert_tracker', '0012_auto_20190606_0924'),
    ]

    operations = [
        migrations.AddField(
            model_name='cert',
            name='expiry_in_years',
            field=models.IntegerField(default=0),
        ),
    ]