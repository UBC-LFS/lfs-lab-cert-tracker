import os
from django.conf import settings
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q
from django.urls import resolve
from django.core.mail import send_mail
import smtplib
from email.mime.text import MIMEText

from .models import UserInactive, Lab, UserLab, Cert, UserCert, LabCert
from . import api


def access_admin_only(view_func):
    """ Access an admin only """

    def wrap(request, *args, **kwargs):
        if request.user.is_superuser is True:
            return view_func(request, *args, **kwargs)
        else:
            raise PermissionDenied
    return wrap


def access_pi_admin(view_func):
    """
    Access for an admin and PI in the area
    Usage: used in AreaDetailsView
    """

    def wrap(request, *args, **kwargs):
        api = Api()
        if request.user.is_superuser is True or api.is_pi_in_area(request.user.id, kwargs['area_id']):
            return view_func(request, *args, **kwargs)
        else:
            raise PermissionDenied

    return wrap


def access_loggedin_user_pi_admin(view_func):
    """
    Access for a loggedin user and a PI in the area and an admin
    Usage: used in UserDetailsView
    """

    def wrap(request, *args, **kwargs):
        api = Api()
        user_id = kwargs['user_id']
        if request.user.id == user_id or request.user.is_superuser is True or user_id in api.get_users_in_area_by_pi(request.user.id):
            return view_func(request, *args, **kwargs)
        else:
            raise PermissionDenied

    return wrap


def access_all(view_func):
    """ Access for all users authenticated """

    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated != True:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrap


def access_loggedin_user_admin(view_func):
    """ Access for a logged-in user or an admin """

    def wrap(request, *args, **kwargs):
        if request.user.is_superuser is True or request.user.id == kwargs['user_id']:
            return view_func(request, *args, **kwargs)
        else:
            raise PermissionDenied
    return wrap


class Api:

    # User
    def get_users(self, option=None):
        """ Get all users """

        if option == 'active':
            return User.objects.filter(is_active=True)

        return User.objects.all().order_by('last_name', 'first_name')

    def get_user(self, attr, by='id'):
        """ Get a user """

        if by == 'username':
            return get_object_or_404(User, username=attr)

        return get_object_or_404(User, id=attr)

    def get_admins(self):
        """ Get all administrators """

        return User.objects.filter(is_superuser=True)

    def add_inactive_users(self, users):
        """ Add inactive status into users """

        for user in users:
            user_inactive = UserInactive.objects.filter(user_id=user.id)
            if user_inactive.exists():
                user.inactive = user_inactive.first()
            else:
                user.inactive = None
        return users


    # Areas
    def get_areas(self):
        """ Get all areas """

        return Lab.objects.all()


    def get_area(self, attr, by='id'):
        """ Get an user or 404 """

        if by == 'name':
            return get_object_or_404(Lab, name=attr)

        return get_object_or_404(Lab, id=attr)


    def add_users_to_areas(self, areas):
        """ Add user info to areas """

        for area in areas:
            area.has_lab_users = []
            area.has_pis = []
            for userlab in area.userlab_set.all():
                if userlab.role == UserLab.LAB_USER:
                    area.has_lab_users.append(userlab.user.id)
                elif userlab.role == UserLab.PRINCIPAL_INVESTIGATOR:
                    area.has_pis.append(userlab.user.id)

        return areas


    # Trainings
    def get_trainings(self):
        """ Get trainings """

        return Cert.objects.all()

    def get_training(self, attr, by='id'):
        """ Get a training """

        if by == 'name':
            return get_object_or_404(Cert, name=attr)

        return get_object_or_404(Cert, id=attr)


    # UserCert

    def get_usercerts(self, option=None):
        """ Get all usercerts """
        if option == 'active':
            return UserCert.objects.filter(user__is_active=True)
        return UserCert.objects.all()


    # UserLab

    def get_userlabs(self):
        return UserLab.objects.all()


    def get_userlab(self, user_id, area_id):
        """ Get a userlab"""

        userlab = UserLab.objects.filter( Q(user_id=user_id) & Q(lab_id=area_id) )
        return userlab.first() if userlab.exists() else None


    def is_pi_in_area(self, user_id, area_id):
        """ Check whether an user is in the area or not """

        return UserLab.objects.filter( Q(user=user_id) & Q(lab=area_id) & Q(role=UserLab.PRINCIPAL_INVESTIGATOR) ).exists()


    def get_users_in_area_by_pi(self, user_id):
        """ Get a list of users in PI's area """

        users = set()

        userlabs = UserLab.objects.filter( Q(user_id=user_id) & Q(role=UserLab.PRINCIPAL_INVESTIGATOR) )
        if userlabs.exists():
            for userlab in userlabs:
                labs = UserLab.objects.filter(lab=userlab.lab.id)
                if labs.exists():
                    for lab in labs:
                        users.add(lab.user.id)

        return list(users)


    def update_or_create_areas_to_user(self, user, areas):
        """ update or create areas to an user """

        all_userlab = user.userlab_set.all()

        report = { 'updated': [], 'created': [], 'deleted': [] }
        used_areas = []
        for area in areas:
            splitted = area.split(',')
            lab = self.get_area(splitted[0])
            role = splitted[1]
            userlab = all_userlab.filter(lab_id=lab.id)
            used_areas.append(lab.id)

            # update or create
            if userlab.exists():
                if userlab.first().role != int(role):
                    updated = userlab.update(role=role)
                    if updated:
                        report['updated'].append(lab.name)
            else:
                created = UserLab.objects.create(user=user, lab=lab, role=role)
                if created:
                    report['created'].append(lab.name)

        for ul in all_userlab:
            if ul.lab.id not in used_areas:
                deleted = ul.delete()
                if deleted:
                    report['deleted'].append(ul.lab.name)

        return report


    # LabCert

    def get_labcerts(self):
        """ Get labcerts """

        return LabCert.objects.all()

    def get_labcert(self, area_id, training_id):
        """ Get a labcert"""

        labcert = LabCert.objects.filter( Q(lab_id=area_id) & Q(cert_id=training_id) )
        return labcert.first() if labcert.exists() else None


    # Utils

    def get_viewing(self, next):
        """ Get viewing information for going back to the previous page """

        split_query = next.split('?')
        res = resolve(split_query[0])

        if res.url_name == 'all_users':
            query = ''
            if len(split_query) > 1: query = split_query[1]

            viewing = { 'page': 'all_users', 'query': query }

        elif res.url_name == 'area_details':
            id = res.kwargs['area_id']
            viewing = { 'page': 'area_details', 'id': id, 'name': self.get_area(id).name }

        return viewing


    def get_error_messages(self, errors):
        """ Get error messages """

        messages = ''
        for key in errors.keys():
            value = errors[key]
            messages += key.replace('_', ' ').upper() + ': ' + value[0]['message'] + ' '
        return messages.strip()


    def check_input_fields(self, request, fields):
        """ Check input fields. Raise a 400 bad request"""

        for field in fields:
            if request.POST.get(field, None) is None:
                raise SuspiciousOperation

    def welcome_message(self):
        """ This is a welcome message"""

        return '''\
        <p>Welcome to LFS!</p>

        <p>
          Thank you for using the LFS Training Record Management System! We want to take this opportunity to introduce you to the <a href="https://my.landfood.ubc.ca/operations/health-and-safety/johsc/" target="_blank">LFS Joint Occupational Health and Safety Committee (JOHSC)</a> and our Local Safety Teams (LSTs). We hope you spend some time to familiarize yourself with your local area’s LST membership and contact information. Below are the four LSTs covering the health and safety of the four main buildings in our faculty:
        </p>

        <ul style="list-style-type:none;">
          <li>
            <a href="https://my.landfood.ubc.ca/operations/health-and-safety/macmillan-lst/" target="_blank">
              MacMillan Local Safety Team (MCML LST)
            </a>
          </li>
          <li>
            <a href="https://my.landfood.ubc.ca/operations/health-and-safety/fnh-lst/" target="_blank">
              Food Nutrition and Health Local Safety Team (FNH LST)
            </a>
          </li>
          <li>
            <a href="https://my.landfood.ubc.ca/operations/health-and-safety/ubc-farm-lst/" target="_blank">
              UBC Farm Local Safety Team (Farm LST)
            </a>
          </li>
          <li>Dairy Centre Local Safety Team (Dairy LST) – coming soon</li>
        </ul>

        <p>
          Thank you for going through all the mandatory health and safety training. What a champion! Please note that if you have not already done so, your supervisor should be reviewing any <a href="https://srs.ubc.ca/health-safety/research-safety/" target="_blank">additional specific training<a/> required for your work duties with you. Your LST may have some safety orientation that is mandatory specific to the building you work in so please check <a href="https://my.landfood.ubc.ca/operations/health-and-safety/lfs-mandatory-training/" target="_blank">mandatory training<a/> for guidelines. Please note that all mandatory training as well as any additional training records should be uploaded to <a href="https://training-report.landfood.ubc.ca" target="_blank">https://training-report.landfood.ubc.ca<a/> via your Campus Wide Login. To access the website off campus, please ensure you connect via <a href="https://it.ubc.ca/services/email-voice-internet/myvpn" target="_blank">UBC VPN</a>.
        </p>

        <p>
          To receive regular updates from our faculty, please subscribe to the appropriate <a href="https://my.landfood.ubc.ca/communications/communication-channels/" target="_blank">communication channels</a> below:
        </p>

        <ul>
          <li>
            LFS Today (Staff and Faculty):
            <a href="https://my.landfood.ubc.ca/lfs-today/" target="_blank">https://my.landfood.ubc.ca/lfs-today/</a>
          </li>
          <li>
            LFS Grad Student Listserve (Grad students):
            email <a href="mailto:lia.maria@ubc.ca">lia.maria@ubc.ca</a>
          </li>
          <li>
            Newslettuce (Undergraduates):
            email <a href="mailto:lfs.programassistant@ubc.ca">lfs.programassistant@ubc.ca</a>
          </li>
        </ul>

        <p>
          If you have any questions, please don’t hesitate to contact us at <a href="mailto:lfs-johsc@lists.ubc.ca">lfs-johsc@lists.ubc.ca</a>.
        </p>
        '''


    def send_notification(self, user):
        """ Send an email when adding a user to a lab and creating new users """

        title = 'You are added to LFS TRMS'

        message = '''\
        <div>
            <p>Hi {0} {1},</p>
            <div>You have recently been added to the LFS Training Record Management System. Please visit <a href={3}>{3}</a> to upload your training records. Thank you.</div>
            <br />
            <div>
                <b>Please note that if you try to access the LFS Training Record Management System off campus,
                you must be connected via
                <a href="https://it.ubc.ca/services/email-voice-internet/myvpn">UBC VPN</a>.</b>
            </div>
            <br />
            <div>{2}</div>
            <br />
            <p>Best regards,</p>
            <p>LFS Training Record Management System</p>
        </div>
        '''.format(user.first_name, user.last_name, self.welcome_message(), os.environ['LFS_LAB_CERT_TRACKER_URL'])

        sent = send_mail(title, message, settings.EMAIL_FROM, [ user.email ], fail_silently=False, html_message=message)
        print('send notification', sent)
        if not sent:
            sent.error = 'Django send_mail went wrong'
        return sent




class Notification(Api):

    def __init__(self):
        """ Constructor """

        self.areas_in_user = self.get_areas_in_user()
        self.trainings_in_user = self.get_trainings_in_user()

        pis_in_area, required_trainings_in_area = self.get_infomation_in_area()
        self.pis_in_area = pis_in_area
        self.required_trainings_in_area = required_trainings_in_area


    def get_areas_in_user(self):
        """ Get areas in user """

        areas_in_user = {}
        for userlab in self.get_userlabs():
            if userlab.user.is_active:
                if userlab.user.id not in areas_in_user:
                    areas_in_user[ userlab.user.id ] = set()

                areas_in_user[ userlab.user.id ].add(userlab.lab.id)

        return areas_in_user

    def get_trainings_in_user(self):
        """ Get trainings in each user """

        trainings_in_user = {}
        for usercert in self.get_usercerts():
            if usercert.user.is_active:
                if usercert.user.id not in trainings_in_user:
                    trainings_in_user[ usercert.user.id ] = set()

                trainings_in_user[ usercert.user.id ].add(usercert.cert.id)

        return trainings_in_user


    def get_infomation_in_area(self):
        """ Get PIs and required trainings in each area """

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
        """ Find missing trainings of each user """

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
        """ Find expired trainings of each user on the target day """

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
        """ Help to find expired trainings  """

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
        """ Send an email with a receiver and a message """

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
        """ Get a base of html template """

        template = """\
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
        """.format(first_name, last_name, message)

        return template


    def get_receiver(self, user):
        """ Get a receiver for an email receiver """

        return '{0} {1} <{2}>'.format(user.first_name, user.last_name, user.email)

    def datetime_to_string(self, datetime):
        """ Convert datetime to string """

        return datetime.strftime('%m/%d/%Y')


    # For missing trainings
    def get_message_lab_users_missing_trainings(self, user_id, missing_trainings):
        """ Get a message for lab users """

        trainings = []
        for training_id in missing_trainings:
            trainings.append('<li>' + self.get_training(training_id).name + '</li>')

        message = """\
            <p>You have missing training(s). Please update it.</p>
            <ul>{0}</ul>
            <p>See <a href="{1}/users/{2}/report">User report</a></p>
        """.format(''.join(trainings), settings.LFS_LAB_CERT_TRACKER_URL, user_id)

        return message


    def get_message_pis_missing_trainings(self, lab_users):
        """ Get a message for PIs """

        lab_users_list = []
        for uid in lab_users:
            lab_users_list.append('<li>' + self.get_user(uid).first_name + ' ' + self.get_user(uid).last_name + '</li>')

        message = """\
            <p>The following users have missing training(s).</p>
            <ul>{0}</ul>
        """.format( ''.join(lab_users_list) )

        return message


    # For expiry trainings
    def get_message_lab_users_expired_trainings(self, trainings, user_id, days, type):
        """ Get a message with a list of users for lab users """

        if type == 'before':
            message = """\
                <p>Your training(s) will expire in {0} days.</p>
                <ul>{1}</ul>
                <p>See <a href="{2}/users/{3}/report">User report</a></p>
                """.format(days, "".join(trainings), settings.LFS_LAB_CERT_TRACKER_URL, user_id)
        else:
            message = """\
                <p>Your training expiration date has already passed. Please update it.</p>
                <ul>{0}</ul>
                <p>See <a href="{1}/users/{2}/report">User report</a></p>
                """.format("".join(trainings), settings.LFS_LAB_CERT_TRACKER_URL, user_id)

        return message


    def get_message_pis_expired_trainings(self, lab_users_list, days, type):
        """ Get a message with a list of users """

        if type == 'before':
            message = """\
                <p>Trainings of the following users in your area will expire in {0} days.</p>
                {1}
            """.format(days, lab_users_list)
        else:
            message = """\
                <p>The following users have expired training(s).</p>
                <ul>{0}</ul>
            """.format(lab_users_list)

        return message


    def send_email_to_lab_users(self, lab_users, days, type):
        """ Send an email to lab users """

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
        """ Send an email to PIs """

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
        """ Send an email to admins """

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
