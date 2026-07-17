from django.contrib.auth.models import User
from django.conf import settings
import smtplib
from email.mime.text import MIMEText
from app import functions as appFunc

from key_request.models import RequestFormStatus, Room, RequestForm, ApprovalGroup
from key_request.utils import APPROVED, EMAIL_FOOTER
from key_request.functions import all_pis_approved, display_user_full_name, display_user_first_name


class ApprovalNotificationManager:

    def __init__(self, request_form_statuses, status, operator):
        self.request_form_statuses = request_form_statuses
        self.status = status
        self.operator = operator

    def _collect_data(self):
        """
        Returns:
          form_pi_rooms    : { form_id: { pi_id: [room, ...] } }
          form_group_rooms : { form_id: { pi_id: { group_id: [room, ...] } } }
          fully_approved   : { form_id: [room, ...] } // ROOMS ARE TRACKED FOR UNIQUENESS
        """
        form_pi_rooms    = {}
        form_group_rooms = {}
        fully_approved   = {}

        seen_rooms_applicant = set()

        for req in self.request_form_statuses:
            room = Room.objects.get(id=req.room_id)
            form_id = int(req.form_id)
            form = RequestForm.objects.get(id=form_id)

            if room.id not in seen_rooms_applicant and all_pis_approved(form, room):
                fully_approved.setdefault(form_id, []).append(room)
                seen_rooms_applicant.add(room.id)

            if req.manager_id:
                self._add_room_to_pi_rooms(form_pi_rooms, form_id, req.manager_id, room)

            if req.group_id:
                group = ApprovalGroup.objects.get(id=req.group_id)
                for member in group.members.all():
                    self._add_room_to_form_group_rooms(form_group_rooms, form_id, member.id, group.id, room)


        return form_pi_rooms, form_group_rooms, fully_approved

    # Add functions -> ensures that ids are always ints

    def _add_room_to_pi_rooms(self, form_pi_rooms_obj, form_id, manager_id, room):
        manager_id = int(manager_id)

        form_pi_rooms_obj \
            .setdefault(form_id, {}) \
            .setdefault(manager_id, []) \
            .append(room)

    def _add_room_to_form_group_rooms(self, form_group_rooms_obj, form_id, member_id, group_id, room):
        member_id = int(member_id)
        group_id = int(group_id)

        form_group_rooms_obj \
            .setdefault(form_id, {}) \
            .setdefault(member_id, {}) \
            .setdefault(group_id, []) \
            .append(room)


    def send_email_notification(self):
        if self.status != APPROVED:
            return

        form_pi_rooms, form_group_rooms, fully_approved = self._collect_data()

        emails_to_send = []

        emails_to_send += self._send_pi_emails(form_pi_rooms, form_group_rooms)
        emails_to_send += self._send_applicant_emails(fully_approved)
        emails_to_send += self._send_admin_emails(fully_approved)
        self._send_multiple(emails_to_send)

    def _send_pi_emails(self, form_pi_rooms, form_group_rooms):
        pi_data = {}

        emails_to_send = []

        all_form_ids = set(form_pi_rooms) | set(form_group_rooms)
        for form_id in all_form_ids:
            for pi_id, rooms in form_pi_rooms.get(form_id, {}).items():
                self._make_pi_data(pi_data, pi_id, form_id, rooms, None)

            for pi_id, groups in form_group_rooms.get(form_id, {}).items():
                self._make_pi_data(pi_data, pi_id, form_id, None, groups)

        for pi_id, forms in pi_data.items():
            pi = User.objects.get(id=pi_id)
            room_info = self._build_per_form_html(forms)

            if self.operator and int(pi_id) == int(self.operator.id):
                subject, body = self._make_operator_message(pi, room_info)
            else:
                subject, body = self._make_manager_message(pi, room_info)

            emails_to_send.append(self._make_send_obj(pi, subject, body))

        return emails_to_send

    def _make_pi_data(self, pi_data_obj, pi_id, form_id, individuals, groups):
        pi_id = int(pi_id)
        form_id = int(form_id)

        pi_form_obj = pi_data_obj \
            .setdefault(pi_id, {}) \
            .setdefault(form_id, {})

        if individuals:
            pi_form_obj['individuals'] = individuals
        if groups:
            pi_form_obj['groups'] = groups

    # applicant email
    def _send_applicant_emails(self, fully_approved):
        emails_to_send = []
        for form_id, rooms in fully_approved.items():
            form = RequestForm.objects.get(id=form_id)
            applicant = form.user
            room_info = self._rooms_to_html(rooms)
            subject, body = self._make_applicant_message(applicant, room_info)
            emails_to_send.append(self._make_send_obj(applicant, subject, body))

        return emails_to_send

    # Admin summary email
    def _send_admin_emails(self, fully_approved):
        emails_to_send = []
        admins = User.objects.filter(is_active=True, is_superuser=True)

        for admin in admins:
            for form_id, rooms in fully_approved.items():
                form = RequestForm.objects.get(id=form_id)
                applicant = form.user
                room_info = self._rooms_to_html(rooms)
                subject, body = self._make_admin_summary_message(admin, applicant, room_info)
                emails_to_send.append(self._make_send_obj(admin, subject, body))

        return emails_to_send

    #HTML

    def _build_per_form_html(self, forms):
        """
        forms: { form_id: { 'individual': [room, ...], 'groups': { group_id: [room, ...] } } }
        Produces one <li> block per applicant.
        """
        sections = []
        for form_id, data in forms.items():
            form = RequestForm.objects.get(id=form_id)
            applicant = form.user

            individual_html = self._rooms_to_html(data.get('individuals', []))
            group_html = self._groups_to_html(data.get('groups', {}))

            sections.append(
                f'<li>'
                f'<strong>{applicant.get_full_name()}\'s request:</strong>'
                f'{individual_html}'
                f'{group_html}'
                f'</li>'
            )

        return '<ul>' + ''.join(sections) + '</ul>'

    def _rooms_to_html(self, rooms):
        if not rooms:
            return ''

        # Only add the room once; keep a set of ids
        seen_rooms = set()
        list_rooms = []
        for room in rooms:
            if room.id not in seen_rooms:
                list_rooms.append(f'<li>{self._display_room(room)}</li>')
                seen_rooms.add(room.id)

        return f'<ul>{"".join(list_rooms)}</ul>'

    def _groups_to_html(self, groups_dict):
        """groups_dict: { group_id: [room, ...] }"""
        if not groups_dict:
            return ''
        items = []
        for group_id, rooms in groups_dict.items():
            group = ApprovalGroup.objects.get(id=group_id)
            items.append(
                f'<li>{group.name}{self._rooms_to_html(rooms)}</li>'
            )
        return '<ul>' + ''.join(items) + '</ul>'

    def _display_room(self, room, option=None):
        ret = '{0} {1} - Room {2}'.format(room.building.code, room.floor.name, room.number)
        if option == 'id':
            ret += f' (ID: {room.id})'
        return ret

    # TEMPLATES

    def _make_manager_message(self, manager, room_info):
        """PI email not the operator."""
        subject = "Notification: Key Request Approval at UBC LFS"
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>This email is to notify you that {1} has approved the following key request(s):</div>
            {2}
            <div>Please visit <a href="{3}">{3}</a> to check the latest status. Thank you.</div>
            {4}
        </div>
        '''.format(
            display_user_first_name(manager),
            display_user_first_name(self.operator),
            room_info,
            settings.SITE_URL,
            EMAIL_FOOTER,
        )
        return subject, message

    def _make_operator_message(self, manager, room_info):
        """PI email as the operator (they did the approving)."""
        subject = "Notification: You Have Approved Key Request(s) at UBC LFS"
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>This email is to confirm that you have approved the following key request(s):</div>
            {1}
            <div>Please visit <a href="{2}">{2}</a> to check the latest status. Thank you.</div>
            {3}
        </div>
        '''.format(
            display_user_first_name(manager),
            room_info,
            settings.SITE_URL,
            EMAIL_FOOTER,
        )
        return subject, message

    def _make_applicant_message(self, user, room_info):
        subject = 'Your key request has been approved by UBC LFS'
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>We are delighted to inform you that your key request has been approved for the following room(s):</div>
            {1}
            <div>Please visit <a href="{2}">{2}</a> to check the status of your key request. Thank you.</div>
            {3}
        </div>
        '''.format(
            user.get_full_name(),
            room_info,
            settings.SITE_URL,
            EMAIL_FOOTER,
        )
        return subject, message

    def _make_admin_summary_message(self, admin, applicant, room_info):
        """Single summary email to the admin with all approved rooms."""
        subject = "Notification: Key Request Approval Summary at UBC LFS"
        message = '''\
        <div>
            <p>Hi {0},</p>
            <div>This email is a notification that {1}'s key request has been approved for the following room(s):</div>
            {2}
            <div>Please visit <a href="{3}">{3}</a> to check the latest status. Thank you.</div>
            {4}
        </div>
        '''.format(
            display_user_first_name(admin),
            display_user_full_name(applicant),
            room_info,
            settings.SITE_URL,
            EMAIL_FOOTER,
        )
        return subject, message

    def _make_send_obj(self, user, subject, message):
        return {
            'user': user,
            'subject': subject,
            'message': message
        }

    def _send_multiple(self, contents):
        try:
            server = smtplib.SMTP(settings.EMAIL_HOST)
            for item in contents:
                user = item['user']
                subject = item['subject']
                message = item['message']
                if settings.EMAIL_FROM and appFunc.check_email_valid(user.email):
                    sender = settings.EMAIL_FROM
                    receiver = '{0} <{1}>'.format(display_user_full_name(user), user.email)

                    print(f'An email notification is sent to {receiver}')

                    msg = MIMEText(message, 'html')
                    msg['Subject'] = subject
                    msg['From'] = sender
                    msg['To'] = receiver
                    server.sendmail(sender, receiver, msg.as_string())
        except Exception as e:
            print(e)
        finally:
            server.quit()

    def _send(self, user, subject, body):
        if settings.EMAIL_FROM and appFunc.check_email_valid(user.email):
            sender = settings.EMAIL_FROM
            receiver = '{0} <{1}>'.format(display_user_full_name(user), user.email)

            print(f'SEND: An email notification is sent to {receiver}')

            msg = MIMEText(body, 'html')
            msg['Subject'] = subject
            msg['From'] = sender
            msg['To'] = receiver

            try:
                server = smtplib.SMTP(settings.EMAIL_HOST)
                server.sendmail(sender, receiver, msg.as_string())
            except Exception as e:
                print(e)
            finally:
                server.quit()