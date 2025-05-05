from django.test import TestCase, Client, tag
from django.urls import reverse
from django.contrib.messages import get_messages
from urllib.parse import urlencode
from django.contrib.auth.models import User, AnonymousUser
import json

from key_request.models import Room, RequestForm, RequestFormStatus

from .utils import APPROVED, DECLINED


ContentType='application/x-www-form-urlencoded'
LOGIN_URL = reverse('accounts:local_login')

DATA = [
    'app/fixtures/certs.json',
    'app/fixtures/labs.json',
    'app/fixtures/users.json',
    'app/fixtures/user_certs.json',
    'app/fixtures/user_labs.json',
    'app/fixtures/lab_certs.json',
    'key_request/fixtures/buildings.json',
    'key_request/fixtures/floors.json',
    'key_request/fixtures/requestform_rooms.json',
    'key_request/fixtures/requestforms.json',
    'key_request/fixtures/requestformstatus.json',
    'key_request/fixtures/room_areas.json',
    'key_request/fixtures/room_managers.json',
    'key_request/fixtures/room_trainings.json',
    'key_request/fixtures/rooms.json'
]


@tag('key_request_test')
class KeyRequestTest(TestCase):
    fixtures = DATA

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.get(username='testadmin')
        cls.pi1 = User.objects.get(username='testpi1')
        cls.user6 = User.objects.get(username='testuser6')


    def login(self, username):
        self.client.post(LOGIN_URL, data={'username': username, 'password': 'password'})
    
    def logout(self):
        self.client.get(reverse('accounts:local_logout'))
    
    def messages(self, res):
        return [m.message for m in get_messages(res.wsgi_request)]
    
    def json_messages(self, res):
        return json.loads(res.content.decode('utf-8'))
    
    def test_check_request_forms(self):
        print('\n- Test: check the number of request forms')
        self.login('testadmin')

        res = self.client.get(reverse('key_request:all_requests'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['total_forms'], 2)

    def test_check_all_request_forms_access_failed_pi1(self):
        print('\n- Test: check all request forms access failed by pi1')
        self.login('testpi1')

        res = self.client.get(reverse('key_request:all_requests'))
        self.assertEqual(res.status_code, 403)
    
    def test_check_all_request_forms_access_failed_user1(self):
        print('\n- Test: check all request forms access failed by user1')
        self.login('testuser1')

        res = self.client.get(reverse('key_request:all_requests'))
        self.assertEqual(res.status_code, 403)

    def test_manager_dashboard_access_manager_success(self):
        print('\n- Test: manager dashboard access - manager - success')
        self.login('testpi1')

        res = self.client.get(reverse('key_request:manager_dashboard'))
        self.assertEqual(res.status_code, 200)
    
    def test_manager_dashboard_access_admin_failure(self):
        print('\n- Test: manager dashboard access - admin - failture')
        self.login('testadmin')

        res = self.client.get(reverse('key_request:manager_dashboard'))
        self.assertEqual(res.status_code, 403)

    def test_manager_dashboard_access_user_failure(self):
        print('\n- Test: manager dashboard access - user - failture')
        self.login('testuser1')

        res = self.client.get(reverse('key_request:manager_dashboard'))
        self.assertEqual(res.status_code, 403)
    

    def test_request_form_approved_by_manger_success(self):
        print('\n- Test: form approved by a manager - success')
        self.login('testpi7')

        data = {
            'form': 2,
            'room': 6,
            'manager': 10,
            'status': '0',
            'next': '/app/key-request/dashboard/'
        }

        res = self.client.post(reverse('key_request:manager_dashboard'), data=urlencode(data), content_type=ContentType)
        msg = self.messages(res)[0]
        self.assertEqual(msg, 'Success! The status of FNH 3rd - Room 310 has been updated.')

        last_status = RequestFormStatus.objects.last()
        self.assertEqual(last_status.form.id, data['form'])
        self.assertEqual(last_status.room.id, data['room'])
        self.assertEqual(last_status.manager.id, data['manager'])
        self.assertEqual(last_status.status, data['status'])

        form = RequestForm.objects.get(id=data['form'])
        room = Room.objects.get(id=data['room'])

        cache = [0] * room.managers.count()
        for i, manager in enumerate(room.managers.all()):
            status_filtered = RequestFormStatus.objects.filter(form_id=form.id, room_id=room.id, manager_id=manager.id)
            if status_filtered.exists():
                for item in status_filtered:
                    if item.status == APPROVED:
                        cache[i] = 1
                        break
        
        count = 0
        for c in cache:
            count += c
        
        if count >= form.rooms.count():
            print('send email')


    def test_request_form_status_failure(self):
        print('\n- Test: form status failure')
        self.login('testpi7')

        data = {
            'form': 2,
            'room': 6,
            'manager': 10,
            'next': '/app/key-request/dashboard/'
        }

        res = self.client.post(reverse('key_request:manager_dashboard'), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 302)
        msg = self.messages(res)[0]
        self.assertEqual(msg, 'Error: A status must be selected.')
    

    def test_request_form_failure(self):
        print('\n- Test: form failure')
        self.login('testpi7')

        data = {
            'room': 6,
            'manager': 10,
            'status': '0',
            'next': '/app/key-request/dashboard/'
        }

        res = self.client.post(reverse('key_request:manager_dashboard'), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 400)


    def test_request_form_decline_manager(self):
        print('\n- Test: form decline')
        self.login('testpi7')

        data = {
            'form': 2,
            'room': 6,
            'manager': 10,
            'status': '1',
            'next': '/app/key-request/dashboard/'
        }

        res = self.client.post(reverse('key_request:manager_dashboard'), data=urlencode(data), content_type=ContentType)
        msg = self.messages(res)[0]
        self.assertEqual(msg, 'Success! The status of FNH 3rd - Room 310 has been updated.')
        
        last_status = RequestFormStatus.objects.last()
        self.assertEqual(last_status.form.id, data['form'])
        self.assertEqual(last_status.room.id, data['room'])
        self.assertEqual(last_status.manager.id, data['manager'])
        self.assertEqual(last_status.status, data['status'])


    def test_user_apply_missing_trainings(self):
        print('\n- Test: user apply - missing trainings')
        self.login('testuser1')

        rooms = ['3']
        session = self.client.session
        session['selected_rooms'] = rooms
        session.save()

        data = {
            'rooms[]': rooms
        }

        res = self.client.post(reverse('key_request:submit_form'), data=urlencode(data), content_type=ContentType)
        self.assertEqual(res.status_code, 404)


    @tag('here')
    def test_user_apply(self):
        print('\n- Test: user apply')

        room_id = 3

        # testuser6
        client_user6 = Client()
        logged_user6 = client_user6.login(username='testuser6', password='password')
        self.assertTrue(logged_user6)

        session = client_user6.session
        session['selected_rooms'] = [room_id]
        session.save()

        data = {
            'user': 16,
            'rooms[]': room_id,
            'role': 'Guest',
            'affliation': 3,
            'employee_number': None,
            'student_number': None,
            'supervisor_first_name': 'John',
            'supervisor_last_name': 'Doe',
            'supervisor_email': 'john.doe@example.com',
            'after_hours_access': 1,
            'working_alone': False,
            'comment': 'Comment',
            'agree': 'yes'
        }

        res = client_user6.post(reverse('key_request:submit_form'), data=urlencode(data), content_type=ContentType)
        msg = self.messages(res)[0]
        self.assertEqual(msg, "Success! test user6's key request form has been submitted.")
        client_user6.logout()


        # testadmin
        client_admin = Client()
        logged_admin = client_admin.login(username='testadmin', password='password')
        self.assertTrue(logged_admin)

        res2 = client_admin.get(reverse('key_request:all_requests'))
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.context['total_forms'], 3)
        client_admin.logout()
        

        form = RequestForm.objects.last()

        # testpi1
        client_pi1 = Client()
        logged_pi1 = client_pi1.login(username='testpi1', password='password')
        self.assertTrue(logged_pi1)

        res3 = client_pi1.get(reverse('key_request:manager_dashboard'))
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(res3.context['total_forms'], 2)
        self.assertEqual(res3.context['num_new_forms'], 1)

        data3_1 = {
            'form': form.id,
            'room': room_id,
            'manager': 4,
            'status': '1',
            'next': '/app/key-request/dashboard/'
        }

        res3_1 = client_pi1.post(reverse('key_request:manager_dashboard'), data=urlencode(data3_1), content_type=ContentType)
        msg3_1 = self.messages(res3_1)[0]
        self.assertEqual(msg3_1, 'Success! The status of MCML 2nd - Room 200 has been updated.')

        last_status3_1 = RequestFormStatus.objects.last()
        self.assertEqual(last_status3_1.form.id, data3_1['form'])
        self.assertEqual(last_status3_1.room.id, data3_1['room'])
        self.assertEqual(last_status3_1.manager.id, data3_1['manager'])
        self.assertEqual(last_status3_1.status, data3_1['status'])


        data3_2 = {
            'form': form.id,
            'room': room_id,
            'manager': 4,
            'status': '2',
            'next': '/app/key-request/dashboard/'
        }

        res3_2 = client_pi1.post(reverse('key_request:manager_dashboard'), data=urlencode(data3_2), content_type=ContentType)
        msg3_2 = self.messages(res3_2)[0]
        self.assertEqual(msg3_2, 'Success! The status of MCML 2nd - Room 200 has been updated.')

        last_status3_2 = RequestFormStatus.objects.last()
        self.assertEqual(last_status3_2.form.id, data3_2['form'])
        self.assertEqual(last_status3_2.room.id, data3_2['room'])
        self.assertEqual(last_status3_2.manager.id, data3_2['manager'])
        self.assertEqual(last_status3_2.status, data3_2['status'])


        data3_3 = {
            'form': form.id,
            'room': room_id,
            'manager': 4,
            'status': '0',
            'next': '/app/key-request/dashboard/'
        }

        res3_3 = client_pi1.post(reverse('key_request:manager_dashboard'), data=urlencode(data3_3), content_type=ContentType)
        msg3_3 = self.messages(res3_3)[0]
        self.assertEqual(msg3_3, 'Success! The status of MCML 2nd - Room 200 has been updated.')

        last_status3_3 = RequestFormStatus.objects.last()
        self.assertEqual(last_status3_3.form.id, data3_3['form'])
        self.assertEqual(last_status3_3.room.id, data3_3['room'])
        self.assertEqual(last_status3_3.manager.id, data3_3['manager'])
        self.assertEqual(last_status3_3.status, data3_3['status'])


        client_pi1.logout()

        # testps3
        client_pi3 = Client()
        logged_pi3 = client_pi3.login(username='testpi3', password='password')
        self.assertTrue(logged_pi3)

        res4 = client_pi3.get(reverse('key_request:manager_dashboard'))
        self.assertEqual(res4.status_code, 200)
        self.assertEqual(res4.context['total_forms'], 1)
        self.assertEqual(res4.context['num_new_forms'], 1)
        
        client_pi3.logout()

        # testps7
        client_pi7 = Client()
        logged_pi7 = client_pi7.login(username='testpi7', password='password')
        self.assertTrue(logged_pi7)

        res5 = client_pi7.get(reverse('key_request:manager_dashboard'))
        self.assertEqual(res5.status_code, 200)
        self.assertEqual(res5.context['total_forms'], 2)
        self.assertEqual(res5.context['num_new_forms'], 2)

        client_pi7.logout()
        



    # apply - 2 managers
    # manger 1 approve
    # manager 2 decline
    # apply - same room
