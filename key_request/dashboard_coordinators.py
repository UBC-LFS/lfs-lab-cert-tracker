from key_request.models import Room, RequestFormStatus, ApprovalGroup, RequestForm
from django.contrib.auth.models import User
from django.db.models import Q, Count, OuterRef, Subquery, Exists
from key_request.functions import has_date_passed, make_request_form_identifier, all_pis_approved
from django.utils import timezone

from key_request.utils import REV_REQUEST_STATUS_DICT, APPROVED, DECLINED, INSUFFICIENT

class RequestFormProcessor:
    user = None
    query = {}
    rooms = []

    def get_all_rooms(self):
        return Room.objects.all()

    def __init__(self, query, user):
        self.query = query
        self.user = user

        # Query items
        # Rooms
        self.building_q = None
        self.floor_q = None
        self.number_q = None
        self._init_room_query()

        # Request Forms
        self.status_q = None
        self.name_q = None
        self._init_form_query()

    def get_all_filtered_rooms(self):
        filtered_rooms = self.get_all_rooms()

        if self.building_q:
            filtered_rooms = filtered_rooms.filter(building__code__exact=self.building_q)
        if self.floor_q:
            filtered_rooms = filtered_rooms.filter(floor__name__exact=self.floor_q)
        if self.number_q:
            filtered_rooms = filtered_rooms.filter(number__exact=self.number_q)

        return filtered_rooms

    def get_total_form_stats(self):
        raise NotImplementedError

   # === Abstract methods ===

    # status depends on scope so very little shared logic

    def get_all_filtered_forms(self):
        raise NotImplementedError

    def _validate_form_status(self, form):
        raise NotImplementedError


    # === Private methods ===

    def _init_room_query(self):
        if not self.query:
            return

        self.building_q = self.query.get('building', None)
        self.floor_q = self.query.get('floor', None)
        self.number_q = self.query.get('number', None)

    def _init_form_query(self):
        if not self.query:
            return

        self.status_q = self.query.get('status', None)
        self.name_q = self.query.get('name', None)

        if self.name_q:
            self.name_q = self.name_q.lower()

    def _validate_name(self, user):
        if not self.name_q:
            return True

        fullname = f"{user.get_full_name().lower()}"

        return self.name_q in fullname

    def _form_matches_filter(self, form):
        return self._validate_form_status(form) and self._validate_name(form.user)

class AdminRequestFormProcessor(RequestFormProcessor):

    def __init__(self, query, user):
        super().__init__(query, user)

        self.request_scope_filters = {}

    def get_all_filtered_forms(self):
        rooms = self.get_all_filtered_rooms()

        forms = RequestForm.objects.filter(rooms__in=rooms, **self.request_scope_filters).distinct().annotate(
            is_new=Q(requestformstatus__isnull=True)
        )

        filtered_forms = []

        for form in forms:
            # need the stats to determine if the status filter matches
            form.status_stats = self._add_overall_status_stats(form)
            if self._form_matches_filter(form):
                filtered_forms.append(form)

        return filtered_forms

    def get_total_form_stats(self):
        result = RequestForm.objects.filter(rooms__in=self.get_all_rooms(), **self.request_scope_filters).aggregate(
            total_forms=Count('pk', distinct=True),
            total_new_forms=Count('pk', filter=Q(requestformstatus__isnull=True), distinct=True),
        )
        return result['total_forms'], result['total_new_forms']

    def _validate_form_status(self, form):

        if not self.status_q:
            # no status query
            return True

        if form.is_new:
            # no status means new
            return self.status_q == "New"

        status = REV_REQUEST_STATUS_DICT.get(self.status_q, -1)

        if status == APPROVED:
            return form.status_stats['total_approved'] == form.status_stats['total_approvers']
        elif status == DECLINED:
            return form.status_stats['total_declined'] > 0
        elif status == INSUFFICIENT:
            return form.status_stats['total_insufficient'] > 0
        else:
            return False

    def _add_overall_status_stats(self, form):

        total_approved = 0
        total_approvers = 0
        total_new = 0
        total_declined = 0
        total_insufficient = 0

        total_rooms_approved = 0

        for room in form.rooms.all():
            is_room_approved = True

            if not room.managers.exists() and not room.groups.exists():
                continue

            # Managers: ALL approve
            manager_ids = room.managers.all().values_list("id", flat=True)
            num_managers = len(manager_ids)
            total_approvers += num_managers

            if num_managers > 0:
                latest_status = RequestFormStatus.objects.filter(
                    form_id=form.id,
                    room_id=room.id,
                    manager_id=OuterRef("pk")
                ).order_by('-created_at')

                managers_with_status = (User.objects.filter(id__in=manager_ids).annotate(
                    latest_status=Subquery(latest_status.values('status')[:1])
                ))

                counts = managers_with_status.aggregate(
                    approved_count=Count('id', filter=Q(latest_status=APPROVED)),
                    declined_count=Count('id', filter=Q(latest_status=DECLINED)),
                    insufficient_count=Count('id', filter=Q(latest_status=INSUFFICIENT))
                )

                total_approved += counts['approved_count']
                total_declined += counts['declined_count']
                total_insufficient += counts['insufficient_count']
                total_new += (num_managers - (counts['approved_count'] + counts['declined_count'] + counts['insufficient_count']))

                if num_managers != counts['approved_count']:
                    is_room_approved = False

            # Groups: at least one approve
            for group in room.groups.all():
                total_approvers += 1

                latest_status = RequestFormStatus.objects.filter(
                    form_id=form.id,
                    room_id=room.id,
                    group_id=group.id
                ).order_by('-created_at').first()

                if latest_status is None:
                    total_new += 1
                    is_room_approved = False
                elif latest_status.status == APPROVED:
                    total_approved += 1
                elif latest_status.status == DECLINED:
                    total_declined += 1
                    is_room_approved = False
                elif latest_status.status == INSUFFICIENT:
                    total_insufficient += 1
                    is_room_approved = False

            if is_room_approved:
                total_rooms_approved += 1

        return {
            'total_rooms': form.rooms.count(),
            'total_rooms_approved': total_rooms_approved,
            'total_approved': total_approved,
            'total_approvers': total_approvers,
            'total_declined': total_declined,
            'total_insufficient': total_insufficient,
            'total_new': total_new
        }

class SupervisorRequestFormProcessor(AdminRequestFormProcessor):

    def __init__(self, query, user):
        super().__init__(query, user)

        self.request_scope_filters = {
            "supervisor": self.user
        }

class ExpiredRequestFormProcessor(AdminRequestFormProcessor):
    def __init__(self, query, user):
        super().__init__(query, user)

        self.request_scope_filters = {
            "expiry_date__lt": timezone.now(),
        }

class ApplicantRequestFormProcessor:

    def __init__(self, user):
        self.user = user

    def get_all_status_annotated_forms(self, forms):

        for form in forms:
            form.status = "Approved"
            latest_status = form.requestformstatus_set.all().order_by('-created_at')
            if latest_status:
                form.status_created_at = latest_status.first().created_at
            for room in form.rooms.all():
                if not(all_pis_approved(form, room)):
                    form.status = 'Pending by Supervisor'
                    form.status_created_at = None
                    break

        return forms

class EntityRequestFormProcessor(RequestFormProcessor):

    def __init__(self, query, user):
        super().__init__(query, user)

        # entity data for form
        self.label = "Entity"
        self.priority = 0

    def get_all_filtered_forms(self):

        # Attach RequestFormStatus & filter
        filtered_rooms = self.get_all_filtered_rooms()
        forms = []
        for room in filtered_rooms:
            for entity_filter in self._get_entity_filters_for_room(room):
                self._set_current_entity(room, **entity_filter)
                latest_status = self._build_latest_status_subquery(room.id, **entity_filter)
                room_forms = self._get_latest_status_room_forms(room, latest_status)
                forms += self._process_room_forms(room, room_forms)
        return forms

    def _build_latest_status_subquery(self, room_id, **entity_filter):
        return RequestFormStatus.objects.filter(
            form_id=OuterRef('pk'),
            room_id=room_id,
            **entity_filter
        ).order_by('-created_at')

    def _get_latest_status_room_forms(self, room, latest_status_subquery):

        room_forms = (
            RequestForm.objects.filter(rooms=room)
            .annotate(
                status=Subquery(latest_status_subquery.values('status')[:1]),
                status_created_at=Subquery(latest_status_subquery.values('created_at')[:1]),
                status_count=Subquery(
                    latest_status_subquery.values('form_id')
                    .annotate(c=Count('id'))
                    .values('c')[:1]
                ),
            )
        )

        return room_forms

    def _get_entity_filters_for_room(self, room):
        """Yield one or more kwarg-dicts to filter RequestFormStatus by, for this room."""
        raise NotImplementedError

    def _process_room_forms(self, room, room_forms):
        processed_forms = []

        for form in room_forms:
            is_new = not form.status_count
            annotated_form = self._annotate_form_object(form, room, is_new)

            if self._form_matches_filter(annotated_form):
                processed_forms.append(annotated_form)

        return processed_forms

    def _set_current_entity(self, room, **entity_filter):
        """Children override this to set self.manager, self.group, etc."""
        pass

    def _validate_form_status(self, form):
        status = form.status

        if not self.status_q:
            return True

        if not status:
            return self.status_q == "New"


        if self.status_q in REV_REQUEST_STATUS_DICT.keys():
            return status == REV_REQUEST_STATUS_DICT.get(self.status_q)

        return False

    def _annotate_form_object(self, form, room, is_new):
        form.is_new = is_new
        form.room = room
        form.priority = self.priority
        form.label = self.label

        form.manager = None
        form.group = None
        return form

    def _get_new_forms_subquery(self):
        return RequestFormStatus.objects.none()

    def get_total_form_stats(self):
        total_forms = 0
        total_new_forms = 0

        for room in self.get_all_rooms():
            for entity_filter in self._get_entity_filters_for_room(room):
                latest_status = self._build_latest_status_subquery(room.id, **entity_filter)
                room_forms = self._get_latest_status_room_forms(room, latest_status)

                total_forms += room_forms.count()
                total_new_forms += room_forms.filter(status_count__isnull=True).count()

        return total_forms, total_new_forms

class GroupFormProcessor(EntityRequestFormProcessor):

    def __init__(self, query, user):
        super().__init__(query, user)

        # The is_active is not required as groups are tied to rooms and inactive groups have 0 rooms
        #  but it is included for future reference that only active rooms are considered valid
        self.user_groups = ApprovalGroup.objects.filter(roles__user=user, is_active=True)

        self.label = "Group"
        self.priority = 1

    def get_all_rooms(self):
        return Room.objects.filter(Q(groups__roles__user=self.user)).distinct()

    def _get_entity_filters_for_room(self, room):
        room_groups = self.user_groups.filter(group_rooms=room)
        for group in room_groups:
            yield {"group_id": group.id}

    def _get_new_forms_subquery(self):
        return RequestFormStatus.objects.filter(
            group__in=self.user_groups,
            form=OuterRef('pk'),
        )

    def _set_current_entity(self, room, **entity_filter):
        group_id = entity_filter.get('group_id')
        self.current_group = self.user_groups.filter(pk=group_id).first() if group_id else None

    def _annotate_form_object(self, form, room, is_new):
        form = super()._annotate_form_object(form, room, is_new)
        form.group = self.current_group
        form.request_form_identifier = make_request_form_identifier(room, form, 'group_id', self.current_group.id)
        return form

class ManagerFormProcessor(EntityRequestFormProcessor):

    def __init__(self, query, user):
        super().__init__(query, user)

        self.label = "Individual"
        self.priority = 2

    def get_all_rooms(self):
        return Room.objects.filter(Q(managers=self.user)).distinct()

    def _get_entity_filters_for_room(self, room):
        yield {"manager_id": self.user.id}

    def _get_new_forms_subquery(self):
        return RequestFormStatus.objects.filter(
            manager=self.user,
            form=OuterRef('pk'),
        )

    def _set_current_entity(self, room, **entity_filter):
        manager_id = entity_filter.get('manager_id')
        self.current_manager = self.user if manager_id == self.user.id else User.objects.filter(pk=manager_id).first()

    def _annotate_form_object(self, form, room, is_new):
        form = super()._annotate_form_object(form, room, is_new)
        form.manager = self.current_manager
        form.request_form_identifier = make_request_form_identifier(room, form, 'manager_id', self.current_manager.id)
        return form

class DashboardCoordinator:

    def __init__(self, user, query, processor_classes=None):
        self.user = user
        self.query = query
        self.num_new_forms = 0
        self.num_total_forms = 0
        self.forms = []
        self.processor_classes = processor_classes or [ManagerFormProcessor, GroupFormProcessor]
        self.processors = [cls(query, user) for cls in self.processor_classes]


    def run(self):
        """runs the processor to get all the forms and sets the internal values"""
        self.num_new_forms = 0
        self.num_total_forms = 0
        self.forms = []

        for processor in self.processors:

            processed_forms = processor.get_all_filtered_forms()

            self.forms += processed_forms
            total_forms, new_forms = processor.get_total_form_stats()

            self.num_total_forms += total_forms
            self.num_new_forms += new_forms

        self.forms = sorted(
            self.forms,
            key=lambda x: (x.submitted_at, getattr(x, "priority", 0) or 0),
            reverse=True
        )

        for i, form in enumerate(self.forms):
            form.counter = len(self.forms) - i

    def get_all_rooms(self):
        """Distinct rooms across every processor, ignoring all filters."""
        rooms_qs = None
        for processor in self.processors:
            qs = processor.get_all_rooms()
            rooms_qs = qs if rooms_qs is None else rooms_qs.union(qs)
        return rooms_qs if rooms_qs is not None else Room.objects.none()

    def get_all_filtered_rooms(self):
        """Distinct rooms across every processor, respecting building/floor/number filters."""
        rooms_qs = None
        for processor in self.processors:
            qs = processor.get_all_filtered_rooms()
            rooms_qs = qs if rooms_qs is None else rooms_qs.union(qs)
        return rooms_qs if rooms_qs is not None else Room.objects.none()

    def get_num_new_forms(self):
        return self.num_new_forms

    def get_forms(self):
        return self.forms

    def get_num_filtered_forms(self):
        return len(self.forms)

    def get_total_forms(self):
        return self.num_total_forms
