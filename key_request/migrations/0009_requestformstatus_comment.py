from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('key_request', '0008_remove_requestform_expiry_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='requestformstatus',
            name='comment',
            field=models.TextField(blank=True, null=True),
        ),
    ]
