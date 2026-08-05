from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from key_request.dashboard_coordinators import ManagerFormProcessor, GroupFormProcessor, DashboardCoordinator
from datetime import timedelta
from django.utils import timezone
from key_request.models import ApprovalGroup, ApprovalGroupRole, RequestFormStatus, Room, RequestForm, Building, Floor
from key_request.utils import REQUEST_STATUS, APPROVED, INSUFFICIENT, DECLINED

LOGIN_URL = reverse('accounts:local_login')

class ApprovalGroupCRUDAndFilterTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='test_admin',
            email='admin@test.com',
            password='password'
        )

        # 1. Create Mock Users
        self.user1 = User.objects.create_user(username='alice', first_name='Alice', last_name='Smith')
        self.user2 = User.objects.create_user(username='bob', first_name='Bob', last_name='Jones')
        self.user3 = User.objects.create_user(username='charlie', first_name='Charlie', last_name='Brown')

        # 2. Create Existing Test Groups
        self.group_alpha = ApprovalGroup.objects.create(name="Alpha Lab")
        users = [self.user1, self.user2]
        group_roles = [
            (ApprovalGroupRole(
                user_id=user.id,
                group_id=self.group_alpha.id
            )) for user in users
        ]
        self.group_beta = ApprovalGroup.objects.create(name="Beta Team")
        group_roles.append(
            ApprovalGroupRole(
                user_id=self.user3.id,
                group_id=self.group_beta.id
            )
        )

        ApprovalGroupRole.objects.bulk_create(group_roles)

        # 3. Login
        self.client.post(LOGIN_URL, data={'username': 'test_admin', 'password': 'password'})

    # ==========================================
    #  TESTING FILTERS (GET /all-groups/)
    # ==========================================
    def test_filter_by_group_name(self):
        response = self.client.get(reverse('key_request:all_groups'), {'name': 'Alpha'})
        self.assertIn(self.group_alpha, response.context['groups'])
        self.assertNotIn(self.group_beta, response.context['groups'])

    def test_filter_by_member_first_name(self):
        response = self.client.get(reverse('key_request:all_groups'), {'member_first_name': 'Bob'})
        self.assertIn(self.group_alpha, response.context['groups'])
        self.assertNotIn(self.group_beta, response.context['groups'])

    def test_filter_by_member_last_name(self):
        response = self.client.get(reverse('key_request:all_groups'), {'member_last_name': 'Brown'})
        self.assertIn(self.group_beta, response.context['groups'])
        self.assertNotIn(self.group_alpha, response.context['groups'])

    def test_filter_by_member_ids_list(self):
        response = self.client.get(reverse('key_request:all_groups') + f"?members[]={self.user1.id}&members[]={self.user2.id}")
        self.assertIn(self.group_alpha, response.context['groups'])

    def test_filter_by_member_ids_list_no_results_for_partial_group_match(self):
        response = self.client.get(reverse('key_request:all_groups') + f"?members[]={self.user1.id}")
        self.assertNotIn(self.group_alpha, response.context['groups'])

    # ==========================================
    #  TESTING CREATION (POST /create-group)
    # ==========================================
    def test_create_group_success(self):
        payload = {
            'name': 'Gamma Lab',
            'member_ids': f"{self.user1.id},{self.user3.id}"
        }
        response = self.client.post(reverse('key_request:create_group'), data=payload)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ApprovalGroup.objects.filter(name='Gamma Lab', is_active=True).exists())

    def test_create_group_success_with_coordinator(self):
        payload = {
            'name': 'Gamma Lab',
            'member_ids': f"{self.user1.id},{self.user3.id}",
            'coordinator_ids': f"{self.user1.id}"
        }
        response = self.client.post(reverse('key_request:create_group'), data=payload)
        self.assertEqual(response.status_code, 302)

        new_group = ApprovalGroup.objects.filter(name='Gamma Lab', is_active=True)
        self.assertTrue(new_group.exists())

        members = ApprovalGroupRole.objects.filter(group_id=new_group.first().id)

        self.assertEqual(members.count(), 2)

        user1_role = ApprovalGroupRole.objects.filter(group_id=new_group.first().id, user_id=self.user1.id)
        user3_role = ApprovalGroupRole.objects.filter(group_id=new_group.first().id, user_id=self.user3.id)

        self.assertTrue(user1_role.exists())
        self.assertTrue(user3_role.exists())

        self.assertEqual(user3_role.first().role, ApprovalGroupRole.Role.MEMBER)
        self.assertEqual(user1_role.first().role, ApprovalGroupRole.Role.COORDINATOR)


    def test_create_fails_without_name(self):
        payload = {
            'name': '',
            'member_ids': f"{self.user1.id}"
        }
        response = self.client.post(reverse('key_request:create_group'), data=payload, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Form is invalid")


    def test_create_fails_with_zero_members(self):
        payload = {
            'name': 'Orphan Group',
            'member_ids': ''
        }
        response = self.client.post(reverse('key_request:create_group'), data=payload, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Form is invalid")

    # ==========================================
    #  TESTING EDITING (POST /edit-group/)
    # ==========================================
    def test_edit_group_fails_with_no_name_or_members(self):
        url = reverse('key_request:edit_group', kwargs={'group_id': self.group_alpha.id})

        response = self.client.post(url, data={'name': '', 'member_ids': f"{self.user1.id}"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Form is invalid")

        response = self.client.post(url, data={'name': 'Alpha New Name', 'member_ids': ''}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Form is invalid")

    # ==========================================
    #  TESTING DELETION (POST /all-groups/change-activation/)
    # ==========================================
    def test_deactivate_group_success(self):
        response = self.client.post(reverse('key_request:change_activation'), data={'group': self.group_alpha.id, 'method': 'deactivate'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ApprovalGroup.objects.filter(id=self.group_alpha.id, is_active=False).exists())

    def test_deactivate_reactivate_group_success(self):
        response = self.client.post(reverse('key_request:change_activation'), data={'group': self.group_alpha.id, 'method': 'deactivate'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ApprovalGroup.objects.filter(id=self.group_alpha.id, is_active=False).exists())
        response = self.client.post(reverse('key_request:change_activation'), data={'group': self.group_alpha.id, 'method': 'activate'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ApprovalGroup.objects.filter(id=self.group_alpha.id, is_active=True).exists())


def make_form(rooms, user, submitted_at=None):
    form = RequestForm.objects.create(
        user=user,
        submitted_at=submitted_at or timezone.now(),
        expiry_date=timezone.now() + timedelta(days=30),
        after_hours_access='1'
    )
    form.rooms.set(rooms)
    return form



class ManagerFormProcessorTests(TestCase):
    """0/1+ managers per room, and the user__in bug."""

    def make_room(self, **kwargs):
        defaults = dict(building_id=self.building.id, floor_id=self.floor.id, number="101")
        defaults.update(kwargs)
        return Room.objects.create(**defaults)

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='test_admin',
            email='admin@test.com',
            password='password'
        )
        self.building = Building.objects.create(id=1, name="Library")
        self.floor = Floor.objects.create(id=1, name="1st")

        self.pi = User.objects.create_user("pi_user")
        self.other_pi = User.objects.create_user("other_pi")

        self.room_with_pi = self.make_room(number="101")
        self.room_with_pi.managers.set([self.pi])

        self.room_no_pi = self.make_room(number="102")

        self.room_other_pi_only = self.make_room(number="103")
        self.room_other_pi_only.managers.set([self.other_pi])

    def test_room_with_no_managers_is_excluded(self):
        """A room with zero managers should never surface for ManagerFormProcessor."""
        processor = ManagerFormProcessor({}, self.pi)
        rooms = processor.get_all_rooms()
        self.assertNotIn(self.room_no_pi, rooms)

    def test_room_with_other_manager_is_excluded(self):
        processor = ManagerFormProcessor({}, self.pi)
        rooms = processor.get_all_rooms()
        self.assertNotIn(self.room_other_pi_only, rooms)

    def test_new_form_has_no_status_and_is_flagged_new(self):
        form = make_form(rooms=[self.room_with_pi], user=self.admin_user)

        processor = ManagerFormProcessor({}, self.pi)
        forms = processor.get_all_filtered_forms()

        self.assertEqual(len(forms), 1)
        self.assertTrue(forms[0].is_new)
        self.assertEqual(forms[0].manager, self.pi)

    def test_form_with_status_is_not_new(self):
        form = make_form(rooms=[self.room_with_pi])
        RequestFormStatus.objects.create(
            form=form,
            room=self.room_with_pi,
            user=self.pi,
            status="Approved",
            created_at=timezone.now(),
        )

        processor = ManagerFormProcessor({}, self.pi)
        forms = processor.get_all_filtered_forms()

        self.assertEqual(len(forms), 1)
        self.assertFalse(forms[0].is_new)
        self.assertEqual(forms[0].status, "Approved")

    def test_get_total_form_stats_does_not_crash_and_counts_correctly(self):
        """
        to find crash bug
        """
        new_form = make_form(rooms=[self.room_with_pi], user=self.admin_user)
        actioned_form = make_form(rooms=[self.room_with_pi], user=self.admin_user)
        RequestFormStatus.objects.create(
            form=actioned_form,
            room=self.room_with_pi,
            user=self.pi,
            status="Approved",
            created_at=timezone.now(),
        )

        processor = ManagerFormProcessor({}, self.pi)
        total, new = processor.get_total_form_stats()

        self.assertEqual(total, 2)
        self.assertEqual(new, 1)


class GroupFormProcessorTests(TestCase):
    """0/1+ groups per room, and the duplicate-room distinct bug."""

    def make_room(self, **kwargs):
        defaults = dict(building_id=self.building.id, floor_id=self.floor.id, number="101")
        defaults.update(kwargs)
        return Room.objects.create(**defaults)

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='test_admin',
            email='admin@test.com',
            password='password'
        )
        self.building = Building.objects.create(id=1, name="Library")
        self.floor = Floor.objects.create(id=1, name="1st")
        self.user = User.objects.create_user("group_member")

        self.group_a = ApprovalGroup.objects.create(name="Group A")
        self.group_b = ApprovalGroup.objects.create(name="Group B")

        ApprovalGroupRole.objects.create(user=self.user, group=self.group_a, role=0)
        ApprovalGroupRole.objects.create(user=self.user, group=self.group_b, role=0)

        self.room_no_group = self.make_room(number="201")

        self.room_one_group = self.make_room(number="202")
        self.room_one_group.groups.set([self.group_a])

        self.room_two_groups = self.make_room(number="203")
        self.room_two_groups.groups.set([self.group_a, self.group_b])

    def test_room_with_no_groups_is_excluded(self):
        processor = GroupFormProcessor({}, self.user)
        rooms = processor.get_all_rooms()
        self.assertNotIn(self.room_no_group, rooms)

    def test_get_all_rooms_is_deduplicated(self):
        """
        ensure if appears twice for same group (e.g. room A -> Group A and Group B; user is in both) only appears once
        """
        processor = GroupFormProcessor({}, self.user)
        rooms = list(processor.get_all_rooms())
        room_ids = [r.id for r in rooms]

        self.assertEqual(
            room_ids.count(self.room_two_groups.id),
            1)

    def test_form_in_room_with_two_groups_produces_one_entry_per_group_not_duplicated(self):
        """
        A form tied to two groups in which a user is in both groups - should be one per group
        """
        form = make_form(rooms=[self.room_two_groups], user=self.admin_user)

        processor = GroupFormProcessor({}, self.user)
        forms = processor.get_all_filtered_forms()

        self.assertEqual(len(forms), 2)
        seen_groups = {f.group.id for f in forms}
        self.assertEqual(seen_groups, {self.group_a.id, self.group_b.id})

    def test_form_with_group_status_is_not_new(self):
        form = make_form(rooms=[self.room_one_group], user=self.admin_user)
        RequestFormStatus.objects.create(
            form=form,
            room=self.room_one_group,
            group=self.group_a,
            operator=self.admin_user,
            status=DECLINED,
            created_at=timezone.now(),
        )

        processor = GroupFormProcessor({}, self.user)
        forms = processor.get_all_filtered_forms()

        self.assertEqual(len(forms), 1)
        self.assertFalse(forms[0].is_new)
        self.assertEqual(forms[0].status, DECLINED)


class MultiRoomFormTests(TestCase):
    """A single form 1+ rooms, mixing manager-only and group-only rooms."""
    def make_room(self, **kwargs):
        defaults = dict(building_id=self.building.id, floor_id=self.floor.id, number="101")
        defaults.update(kwargs)
        return Room.objects.create(**defaults)


    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='test_admin',
            email='admin@test.com',
            password='password'
        )
        self.building = Building.objects.create(id=1, name="Library")
        self.floor = Floor.objects.create(id=1, name="1st")
        self.pi = User.objects.create_user("multi_room_pi")
        self.group = ApprovalGroup.objects.create(name="Multi Room Group")
        ApprovalGroupRole.objects.create(user=self.pi, group=self.group, role=0)

        self.room_manager = self.make_room(number="301")
        self.room_manager.managers.set([self.pi])

        self.room_group = self.make_room(number="302")
        self.room_group.groups.set([self.group])

    def test_form_across_two_rooms_surfaces_under_both_processors(self):
        form = make_form(rooms=[self.room_manager, self.room_group], user=self.admin_user)

        coordinator = DashboardCoordinator(
            self.pi, {}, processor_classes=[ManagerFormProcessor, GroupFormProcessor]
        )
        coordinator.run()

        labels = sorted(f.label for f in coordinator.get_forms())
        self.assertEqual(labels, ["Group Form", "PI Form"])

    def test_dashboard_coordinator_does_not_double_count_total_forms(self):
        """
        ensures total is not manager + group
        """
        make_form(rooms=[self.room_manager, self.room_group], user=self.admin_user)

        coordinator = DashboardCoordinator(
            self.pi, {}, processor_classes=[ManagerFormProcessor, GroupFormProcessor]
        )
        coordinator.run()

        # one form counted once under each processor's own room scope
        self.assertEqual(coordinator.get_total_forms(), 2)


class GroupTotalFormStatsTests(TestCase):
    """Count(distinct=True, filter=...) correctness for the group processor."""
    def make_room(self, **kwargs):
        defaults = dict(building_id=self.building.id, floor_id=self.floor.id, number="101")
        defaults.update(kwargs)
        return Room.objects.create(**defaults)

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='test_admin',
            email='admin@test.com',
            password='password'
        )
        self.building = Building.objects.create(id=1, name="Library")
        self.floor = Floor.objects.create(id=1, name="1st")
        self.user = User.objects.create_user("stats_user")
        self.group = ApprovalGroup.objects.create(name="Stats Group")
        ApprovalGroupRole.objects.create(user=self.user, group=self.group, role=0)

        self.room = self.make_room(number="401")
        self.room.groups.set([self.group])

    def test_total_and_new_counts_are_not_inflated_by_join(self):
        """
        Confirm request only counted once
        """
        form = make_form(rooms=[self.room], user=self.admin_user)
        RequestFormStatus.objects.create(
            form=form, room=self.room, group=self.group, operator=self.admin_user,
            status=INSUFFICIENT, created_at=timezone.now() - timedelta(days=1),
        )
        RequestFormStatus.objects.create(
            form=form, room=self.room, group=self.group, operator=self.admin_user,
            status=APPROVED, created_at=timezone.now(),
        )

        processor = GroupFormProcessor({}, self.user)
        total, new = processor.get_total_form_stats()

        self.assertEqual(total, 1)
        self.assertEqual(new, 0)

    def test_new_form_with_zero_statuses_counts_as_new(self):
        make_form(rooms=[self.room], user=self.admin_user)

        processor = GroupFormProcessor({}, self.user)
        total, new = processor.get_total_form_stats()

        self.assertEqual(total, 1)
        self.assertEqual(new, 1)