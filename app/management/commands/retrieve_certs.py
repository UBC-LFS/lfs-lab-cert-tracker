import requests
from datetime import datetime, date
from django.conf import settings
from django.core.management.base import BaseCommand
import lfs_lab_cert_tracker.models as models
from app.utils import Api
from app import api
from django.db.models import Q

class Command(BaseCommand):
    help = 'Retrieve certificates from the API and save to UserApiCerts model'

    api = Api()
        
    def handle(self, *args, **options):
        # Find users who have missing certs
        all_users = self.api.get_users()
        user_list = []
        for user in api.add_missing_certs(all_users):
            if user.missing_certs != None:
                user_list.append(user)


        for user in user_list:
            try:
                certificates = self.api.get_certificates_for_user(user.username)
                certificates = []
                for cert in certificates:
                    completion_date_str = cert['certificate']['completionDate']
                    completion_date = date(
                        year=int(completion_date_str[:4]),
                        month=int(completion_date_str[5:7]),
                        day=int(completion_date_str[8:10])
                    )
                    
                    # Check if a UserApiCerts instance already exists with the same user, name, and completion date
                    existing_cert = models.UserApiCerts.objects.filter(
                        Q(user=user) &
                        Q(training_name=cert['certificate']['trainingName']) &
                        Q(completion_date=completion_date)
                    ).first()
                    
                    if existing_cert:
                        print("Certificate already exists for", user.username)
                        continue
                    
                    # Create a UserApiCerts instance and save it to the database
                    models.UserApiCerts.objects.create(
                        user=user,
                        training_name=cert['certificate']['trainingName'],
                        completion_date=completion_date
                    )
                    print("Created certificate for", user.username)
            
            except Exception as e:
                # Handle any exceptions that occurred during the API request
                print(f"An error occurred for user {user.username}: {str(e)}")