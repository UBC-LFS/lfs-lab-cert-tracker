import os
import smtplib, ssl
from email.mime.text import MIMEText

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from lfs_lab_cert_tracker.models import Cert, Lab, UserCert, UserLab, LabCert


class Api:

    # User
    def get_users(self, option=None):
        ''' Get all users '''
        if option == 'active':
            return User.objects.filter(is_active=True)
        return User.objects.all()

    def get_user(self, attr, by='id'):
        ''' Get a user '''

        if by == 'username':
            return get_object_or_404(User, username=attr)

        return get_object_or_404(User, id=attr)

    def get_admins(self):
        return User.objects.filter(is_superuser=True)



    # Cert
    def get_trainings(self):
        ''' Get trainings '''

        return Cert.objects.all()

    def get_training(self, attr, by='id'):
        ''' Get a training '''

        if by == 'name':
            return get_object_or_404(Cert, name=attr)

        return get_object_or_404(Cert, id=attr)


    # UserCert
    def get_usercerts(self, option=None):
        if option == 'active':
            return UserCert.objects.filter(user__is_active=True)
        return UserCert.objects.all()


    # UserLab
    def get_userlabs(self):
        return UserLab.objects.all()


    # LabCert
    def get_labcerts(self):
        return LabCert.objects.all()


class Notification(Api):

    def __init__(self):
        ''' Constructor '''

        self.areas_in_user = self.get_areas_in_user()
        self.trainings_in_user = self.get_trainings_in_user()

        pis_in_area, required_trainings_in_area = self.get_infomation_in_area()
        self.pis_in_area = pis_in_area
        self.required_trainings_in_area = required_trainings_in_area

        #print(self.areas_in_user)
        #print(self.pis_in_area)
        #print(self.required_trainings_in_area)
        #print('----------------------------')

    def get_areas_in_user(self):
        ''' Get areas in user '''

        areas_in_user = {}
        for userlab in self.get_userlabs():
            if userlab.user.is_active:
                if userlab.user.id not in areas_in_user:
                    areas_in_user[ userlab.user.id ] = set()

                areas_in_user[ userlab.user.id ].add(userlab.lab.id)

        return areas_in_user

    def get_trainings_in_user(self):
        ''' Get trainings in each user '''

        trainings_in_user = {}
        for usercert in self.get_usercerts():
            if usercert.user.is_active:
                if usercert.user.id not in trainings_in_user:
                    trainings_in_user[ usercert.user.id ] = set()

                trainings_in_user[ usercert.user.id ].add(usercert.cert.id)

        return trainings_in_user


    def get_infomation_in_area(self):
        ''' Get PIs and required trainings in each area '''

        pis_in_area = {}
        required_trainings_in_area = {}

        # Get PIs in each area
        for userlab in self.get_userlabs():
            if userlab.user.is_active:
                if userlab.role == UserLab.PRINCIPAL_INVESTIGATOR:
                    if userlab.lab.id not in pis_in_area.keys():
                        pis_in_area[ userlab.lab.id ] = set()

                    pis_in_area[ userlab.lab.id ].add(userlab.user.id)

        # Get required trainings in each area
        for labcert in self.get_labcerts():
            if labcert.lab.id not in required_trainings_in_area.keys():
                required_trainings_in_area[ labcert.lab.id ] = set()

            required_trainings_in_area[ labcert.lab.id ].add(labcert.cert.id)

        return pis_in_area, required_trainings_in_area


    def find_missing_trainings(self):
        ''' Find missing trainings of each user '''

        lab_users = []
        pis = {}

        # Create a set of PIs
        for area_id, supervisors in self.pis_in_area.items():
            for supervisor in supervisors:
                if supervisor not in pis.keys():
                    pis[supervisor] = set()

        # Insert users when missing trainings exist
        for user in self.get_users('active'):
            if user.userlab_set.count() > 0:
                missing_trainings = set()

                for userlab in user.userlab_set.all():
                    temp_missing_trainings = set()
                    if userlab.lab.id in self.required_trainings_in_area.keys():
                        if userlab.user.id in self.trainings_in_user.keys():
                            temp_missing_trainings = self.required_trainings_in_area[ userlab.lab.id ] - self.trainings_in_user[ userlab.user.id ]
                        else:
                            temp_missing_trainings = self.required_trainings_in_area[ userlab.lab.id ]

                    # If there are some missing trainings found, then add PIs in thi work area
                    if len(temp_missing_trainings) > 0:
                        supervisors = self.pis_in_area[ userlab.lab.id ]
                        for supervisor in supervisors:
                            pis[supervisor].add(user.id)

                    # Update some of missing trainings to a set of missing trainings
                    missing_trainings.update(temp_missing_trainings)

                if len(missing_trainings) > 0:
                    lab_users.append({ 'id': user.id, 'user': user, 'missing_trainings': list(missing_trainings) })

        return lab_users, pis


    def find_expired_trainings(self, target_day, type):
        ''' Find expired trainings of each user on the target day '''

        lab_users = []
        pis = {}

        for user in self.get_users('active'):
            if user.usercert_set.count() > 0:
                lab_user = { 'id': user.id, 'trainings': [] }

                for usercert in user.usercert_set.all():
                    if usercert.completion_date != usercert.expiry_date:

                        if type == 'before':
                            if usercert.expiry_date == target_day:
                                lab_user, pis = self.help_find_expired_trainings(user, usercert, lab_user, pis)

                        elif type == 'after':
                            if usercert.expiry_date < target_day:
                                lab_user, pis = self.help_find_expired_trainings(user, usercert, lab_user, pis)

                if len(lab_user['trainings']) > 0:
                    lab_users.append(lab_user)

        return lab_users, pis


    def help_find_expired_trainings(self, user, usercert, lab_user, pis):
        ''' Help to find expired trainings  '''

        for userlab in user.userlab_set.all():
            if usercert.cert.id in self.required_trainings_in_area[userlab.lab.id]:
                info = {
                    'id': usercert.cert.id,
                    'training': usercert.cert,
                    'completion_date': usercert.completion_date,
                    'expiry_date': usercert.expiry_date
                }

                # Check if training contains or not in the list of trainings of a lab user
                if usercert.cert.id not in [ training['id'] for training in lab_user['trainings'] ]:
                    lab_user['trainings'].append(info)

                # Insert PIs in this work area
                for pi in self.pis_in_area[userlab.lab.id]:
                    if pi not in pis.keys(): pis[pi] = dict()
                    if user.id not in pis[pi]: pis[pi][user.id] = []

                    pis[pi][user.id].append(info)

        return lab_user, pis




    # Methods to send emails

    def send_email(self, receiver, message):
        ''' Send an email with a receiver and a message '''

        password = None
        port = None

        sender = os.environ['LFS_LAB_CERT_TRACKER_EMAIL_FROM']
        msg = MIMEText(message, 'html')
        msg['Subject'] = 'Training Record Notification'
        msg['From'] = sender
        msg['To'] = receiver

        try:
        	server = smtplib.SMTP(os.environ['LFS_LAB_CERT_TRACKER_EMAIL_HOST'])
        	#server.ehlo()
        	#server.starttls(context=ssl.create_default_context())
        	#server.ehlo()
        	#server.login(sender_email, password)
        	server.sendmail(sender, receiver, msg.as_string())
        except Exception as e:
        	print(e)
        finally:
        	server.quit()


    def html_template(self, first_name, last_name, message):
        ''' Get a base of html template '''

        template = '''\
        <html>
          <head></head>
          <body>
            <p>Hi {0} {1},</p>
            <div>{2}</div>
            <br />
            <div>
                <b>Please note that if you try to access the LFS Training Record Management System off campus,
                you must be connected via
                <a href="https://it.ubc.ca/services/email-voice-internet/myvpn">UBC VPN</a>.</b>
            </div>
            <br /><br />
            <div>
                If you are trying to enroll in a missing or expired training, or to retrieve the training completion record, please visit the following links to get to the appropriate sites:
                <p>
                    <b>UBC/LFS Mandatory Training</b><br />
                    <a href="https://my.landfood.ubc.ca/lfs-mandatory-training">https://my.landfood.ubc.ca/lfs-mandatory-training</a>
                </p>
            </div>
            <br />
            <p>Best regards,</p>
            <p>LFS Training Record Management System</p>
          </body>
        </html>
        '''.format(first_name, last_name, message)

        return template


    def get_receiver(self, user):
        ''' Get a receiver for an email receiver '''

        return '{0} {1} <{2}>'.format(user.first_name, user.last_name, user.email)

    def datetime_to_string(self, datetime):
        ''' Convert datetime to string '''

        return datetime.strftime('%m/%d/%Y')


    # For missing trainings
    def get_message_lab_users_missing_trainings(self, user_id, missing_trainings):
        ''' Get a message for lab users '''

        trainings = []
        for training_id in missing_trainings:
            trainings.append('<li>' + self.get_training(training_id).name + '</li>')

        message = '''\
            <p>You have missing training(s). Please update it.</p>
            <ul>{0}</ul>
            <p>See <a href="{1}/users/{2}/report">User report</a></p>
        '''.format(''.join(trainings), settings.LFS_LAB_CERT_TRACKER_URL, user_id)

        return message


    def get_message_pis_missing_trainings(self, lab_users):
        ''' Get a message for PIs '''

        lab_users_list = []
        for uid in lab_users:
            lab_users_list.append('<li>' + self.get_user(uid).first_name + ' ' + self.get_user(uid).last_name + '</li>')

        message = '''\
            <p>The following users have missing training(s).</p>
            <ul>{0}</ul>
        '''.format( ''.join(lab_users_list) )

        return message


    # For expiry trainings
    def get_message_lab_users_expired_trainings(self, trainings, user_id, days, type):
        ''' Get a message with a list of users for lab users '''

        if type == 'before':
            message = '''\
                <p>Your training(s) will expire in {0} days.</p>
                <ul>{1}</ul>
                <p>See <a href="{2}/users/{3}/report">User report</a></p>
                '''.format(days, "".join(trainings), settings.LFS_LAB_CERT_TRACKER_URL, user_id)
        else:
            message = '''\
                <p>Your training expiration date has already passed. Please update it.</p>
                <ul>{0}</ul>
                <p>See <a href="{1}/users/{2}/report">User report</a></p>
                '''.format("".join(trainings), settings.LFS_LAB_CERT_TRACKER_URL, user_id)

        return message


    def get_message_pis_expired_trainings(self, lab_users_list, days, type):
        ''' Get a message with a list of users '''

        if type == 'before':
            message = '''\
                <p>Trainings of the following users in your area will expire in {0} days.</p>
                {1}
            '''.format(days, lab_users_list)
        else:
            message = '''\
                <p>The following users have expired training(s).</p>
                <ul>{0}</ul>
            '''.format(lab_users_list)

        return message


    def send_email_to_lab_users(self, lab_users, days, type):
        ''' Send an email to lab users '''

        for lab_user in lab_users:
            user_id = lab_user['id']

            if len(lab_user['trainings']) > 0:
                user = self.get_user(user_id)

                trainings = []
                for item in lab_user['trainings']:
                    trainings.append('<li>' + item['training'].name + ' (Expiry Date: ' + self.datetime_to_string(item['expiry_date']) + ')</li>')

                receiver = self.get_receiver(user)
                message = self.get_message_lab_users_expired_trainings(trainings, user_id, days, type)
                template = self.html_template(user.first_name, user.last_name, message)

                self.send_email(receiver, template)
                print( 'User: Sent it to {0}'.format(receiver) )


    def send_email_to_pis(self, pis, days, type):
        ''' Send an email to PIs '''

        for pid, lab_users in pis.items():

            if len(lab_users) > 0:
                contents = []
                for user_id, trainings in lab_users.items():

                    if len(trainings) > 0:
                        pi = self.get_user(pid)
                        user = self.get_user(user_id)

                        content = '<div>' + user.first_name + ' ' + user.last_name + '</div><ul>'
                        for item in trainings:
                            content += '<li>' + item['training'].name + ' (Expiry Date: ' + self.datetime_to_string(item['expiry_date']) + ')</li>'
                        content += '</ul><br />'
                        contents.append(content)

                if len(contents) > 0:
                    lab_users_list =  ''.join(contents)

                    pi = self.get_user(pid)
                    receiver = self.get_receiver(pi)
                    message = self.get_message_pis_expired_trainings(lab_users_list, days, type)
                    template = self.html_template(pi.first_name, pi.last_name, message)

                    self.send_email(receiver, template)
                    print( "Supervisor: Sent it to {0}".format(receiver) )

    def send_email_to_admins(self, admins, lab_users, days, type):
        ''' Send an email to admins '''

        contents = []
        for lab_user in lab_users:
            user_id = lab_user['id']
            user = self.get_user(user_id)
            content = '<div>' + user.first_name + ' ' + user.last_name + " (<a href='" + settings.LFS_LAB_CERT_TRACKER_URL + '/users/' + str(user_id) + "/report'>User report</a>)</div><ul>"

            for item in lab_user['trainings']:
                content += '<li>' + item['training'].name + ' (Expiry Date: ' + self.datetime_to_string(item['expiry_date']) + ')</li>'

            content += '</ul>'
            contents.append(content)

        lab_users_list = ''.join(contents)

        for admin in admins:
            receiver = self.get_receiver(admin)
            message = self.get_message_pis_expired_trainings(lab_users_list, days, type)
            template = self.html_template('LFS TRMS', 'administrators', message)

            self.send_email(receiver, template)
            print( 'Admin: Sent it to {0}'.format(receiver) )
