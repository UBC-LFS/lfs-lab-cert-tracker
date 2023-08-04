import requests
from datetime import datetime, date, timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
import lfs_lab_cert_tracker.models as models
from app.utils import Api
from app import api
from django.db.models import Q
import re

def do_names_match(string1, string2):
    """
    Check if string1 matches string2 according to these rules:
    
    1. Removes words enclosed in parentheses from string1.
    2. Removes the word 'Online' from string1 if it exists. This is for the missmatch: Privacy & Information Security - Fundamentals Part 1 Online
    3. Splits string1 into words, allowing alphanumeric words that start with a capital letter or digit.
    4. Converts the words from string1 and string2 to lowercase for case-insensitive comparison.
    5. Checks if each word from string1 is present in string2.

    Args:
        string1 (str): The first string to compare.
        string2 (str): The second string to compare.

    Returns:
        bool: True if all words from string1 are found in string2; False otherwise.
    """
    string1 = re.sub(r'\([^()]*\)', '', string1)
    
    # Remove the word 'Online' from string1 if it exists
    string1 = string1.replace('Online', '')
    
    words1 = re.findall(r'\b(?:[A-Z]\w*|\d+)\b', string1)
    
    words1 = [word.lower() for word in words1]
    string2 = string2.lower()

    for word in words1:
        if word not in string2:
            return False
    
    return True


class Command(BaseCommand):
    help = 'Retrieve certificates from the API and save to UserApiCerts model'

    api = Api()
        
    def handle(self, *args, **options):
        # Find users who have missing certs
        all_users = self.api.get_users(option='active')
        user_list = api.get_users_with_missing_certs(all_users)

        for user in user_list:
            try:
                print("CALLING API FOR", user.username)
                certificates = self.api.get_certificates_for_cwls([user.username])
                for cert in certificates:
                    completion_date_str = cert['certificate']['completionDate']
                    completion_date = date(
                        year=int(completion_date_str[:4]),
                        month=int(completion_date_str[5:7]),
                        day=int(completion_date_str[8:10])
                    )
                    
                    # Check if a UserApiCerts instance already exists with the same user, name, and completion date
                    api_cert = models.UserApiCerts.objects.filter(
                        Q(user=user) &
                        Q(training_name=cert['certificate']['trainingName']) &
                        Q(completion_date=completion_date)
                    ).first()
                    
                    if not api_cert:
                        # Create a UserApiCerts instance and save it to the database
                        api_cert = models.UserApiCerts.objects.create(
                            user=user,
                            training_name=cert['certificate']['trainingName'],
                            completion_date=completion_date
                        )
                    
                    # Check user missing certs and try to create certificate if names match
                    for missing_cert in user.missing_certs.all():
                        if do_names_match(api_cert.training_name, missing_cert.cert.name):
                            res = api.update_or_create_user_cert(user_id=user.id, cert_id=missing_cert.cert.id, cert_file=None, completion_date=api_cert.completion_date, expiry_date=api_cert.completion_date + timedelta(days=365 * missing_cert.cert.expiry_in_years))
                            print(f"AUTO ADD {missing_cert.cert.name} WITH RESULT: {res}")
                            res2 = self.api.remove_missing_cert(user.id, missing_cert.cert.id)
                            break

                    # Check for user expired certs and try to add upated certificate
                    user_expired_certs = api.get_expired_usercerts(user.id)
                    for existing_cert in user_expired_certs:
                        if do_names_match(api_cert.training_name, existing_cert.cert.name):
                            if existing_cert.completion_date < api_cert.completion_date:
                                created = api.update_or_create_user_cert(user_id=user.id, cert_id=existing_cert.cert.id, cert_file=None, completion_date=api_cert.completion_date, expiry_date=api_cert.completion_date + timedelta(days=365 * missing_cert.cert.expiry_in_years))
                                if created:
                                    print(f"AUTO ADD NEWER CERT {existing_cert.cert.name} FOR {user.username}")
                                    break

            except Exception as e:
                # Handle any exceptions that occurred during the API request
                print(f"An error occurred for user {user.username}: {str(e)}")