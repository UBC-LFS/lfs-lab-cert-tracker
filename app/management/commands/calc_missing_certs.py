import requests
from datetime import datetime, date, timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
import lfs_lab_cert_tracker.models as models
from app.utils import Api
from app import api
from django.db.models import Q
import re

class Command(BaseCommand):
    help = 'Get all the missing certs calculated manually'

    api = Api()
        
    def handle(self, *args, **options):
        # Find users who have missing certs
        all_users = self.api.get_users()
        missing_certs_dict = {}
        count = 0
        for user in all_users:
            missing = api.get_missing_certs_obj(user.id)
            missing_certs_dict[user.id] = missing
            count += len(missing)
            for cert in missing:
                cert.source, created = models.MissingCert.objects.get_or_create(user=user, cert=cert)
                if created:
                    print("CERT CREATED", cert.source)
            
        print("LENGTH IS", count)
        print("LENGTH OF ALL MISSING CERTS IS", models.MissingCert.objects.all().count())