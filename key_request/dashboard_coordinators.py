from key_request.models import Room, RequestFormStatus, ApprovalGroup, RequestForm
from django.contrib.auth.models import User
from django.db.models import Q, Count, OuterRef, Subquery, Exists
from key_request.functions import has_date_passed

from key_request.utils import REV_REQUEST_STATUS_DICT

class RequestFormProcessor:
    user = None
    query = {}
    rooms = []

    def get_all_rooms(self):
        return Room.objects.all()

    def __init__(self, query, user):
        self.query = query
        self.user = user

        self.label = "Form"
        self.priority = 0

        # Query items
        # Rooms
        self.building_q = None
        self.floor_q = None
        self.number_q = None
        self._init_room_query()

        # Key Request Forms
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

    def get_all_filtered_forms(self):

        rooms = self.get_all_filtered_rooms()

        latest_status_sq = RequestFormStatus.objects.filter(
            form_id=OuterRef('pk'),
            room__in=rooms,
        ).order_by('-created_at').values('status')[:1]

        forms = RequestForm.objects.filter(rooms__in=rooms).distinct().annotate(
            status=Subquery(latest_status_sq)
        )
        filtered_forms = []

        for form in forms:
            if self._form_matches_filter(form):
                is_new = False if form.status else True
                form = self._annotate_form_object(form, None, is_new)
                filtered_forms.append(form)

        return filtered_forms

    def get_total_form_stats(self):

        result = RequestForm.objects.filter(rooms__in=self.get_all_rooms()).aggregate(
            total_forms=Count('pk', distinct=True),
            total_new_forms=Count('pk', filter=Q(requestformstatus__isnull=True), distinct=True),
        )
        return result['total_forms'], result['total_new_forms']

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

    def _validate_form_status(self, status):
        if not self.status_q:
            return True

        if not status:
            return self.status_q == "New"

        if status in REV_REQUEST_STATUS_DICT.keys():
            return status == REV_REQUEST_STATUS_DICT.get(self.status_q)

        return False

    def _validate_name(self, user):
        if not self.name_q:
            return True

        fullname = f"{user.get_full_name().lower()}"

        return self.name_q in fullname

    def _form_matches_filter(self, form):
        return self._validate_form_status(form.status) and self._validate_name(form.user)

    def _annotate_form_object(self, form, room, is_new):
        form.is_new = is_new
        form.label = self.label
        form.priority = self.priority
        form.room = room
        return form

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

    def _annotate_form_object(self, form, room, is_new):
        super()._annotate_form_object(form, room, is_new)
        form.manager = None
        form.group = None
        return form

    def _get_new_forms_subquery(self):
        return RequestFormStatus.objects.none()

    def get_total_form_stats(self):
        rooms = self.get_all_rooms()

        if not rooms:
            return 0, 0

        request_form_status_query = self._get_new_forms_subquery()

        result = RequestForm.objects.filter(rooms__in=self.get_all_rooms()).aggregate(
            total_forms=Count('pk', distinct=True),
            total_new_forms=Count('pk', filter=~Exists(request_form_status_query), distinct=True),
        )
        return result['total_forms'], result['total_new_forms']


class GroupFormProcessor(EntityRequestFormProcessor):

    def __init__(self, query, user):
        super().__init__(query, user)

        self.user_groups = ApprovalGroup.objects.filter(roles__user=user)

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
        return form



class ExpiredRequestFormProcessor(RequestFormProcessor):

    def _form_matches_filter(self, form):
        return has_date_passed(form.expiry_date) and super()._form_matches_filter(form)

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

        self.forms = sorted(self.forms, key=lambda x: (x.submitted_at, x.priority), reverse=True)
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
