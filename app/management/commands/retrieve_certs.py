import requests
from datetime import datetime, date
from django.conf import settings
from django.core.management.base import BaseCommand
import lfs_lab_cert_tracker.models as models
from app.utils import Api

class Command(BaseCommand):
    help = 'Retrieve certificates from the API and save to UserApiCerts model'

    cwls = []

    api = Api()
    
    def handle(self, *args, **options):
        # Retrieve certificates for each user with CWL in the cwls list
        for user in models.AuthUser.objects.filter(username__in=self.cwls):
            try:
                certificates = self.api.get_certificates_for_user(user.username)
                for cert in certificates:
                    print("CERT IS", cert, cert['certificate'])
                    print("CREATED CERTFICATE FOR", user.username)
                    # Create a UserApiCerts instance and save it to the database
                    completion_date_str = cert['certificate']['completionDate']
                    completion_date = date(
                        year=int(completion_date_str[:4]),
                        month=int(completion_date_str[5:7]),
                        day=int(completion_date_str[8:10])
                    )
                    models.UserApiCerts.objects.create(
                        user=user,
                        training_name=cert['certificate']['trainingName'],
                        completion_date=completion_date
                    )
            except Exception as e:
                # Handle any exceptions that occurred during the API request
                print(f"An error occurred for user {user.username}: {str(e)}")