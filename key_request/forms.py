from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from .models import *

class BuildingForm(forms.ModelForm):
    class Meta:
        model = Building
        fields = ['name', 'code']
        widgets = {
            'name': forms.TextInput(attrs={ 'class': 'form-control' }),
            'code': forms.TextInput(attrs={ 'class': 'form-control' })
        }
        help_texts = {
            'name': 'Maximum characters: 100',
            'code': 'It must be unique. Maximum characters: 20'
        }


class FloorForm(forms.ModelForm):
    class Meta:
        model = Floor
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={ 'class': 'form-control' })
        }
        help_texts = {
            'name': 'It must be unique. Maximum characters: 50'
        }

class RoomGroupForm(forms.ModelForm):

    search_name = forms.CharField(
        label="User Search",
        widget=
        forms.TextInput(
            attrs={
                'id': 'id_user_name_search',
                'data-url': '',
                'class': 'form-control form-control-sm',
                'placeholder': 'Type the user\'s name to search...'
            }
        ),
        required=False)

    member_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )

    class Meta:
        model = RoomGroup
        fields = ['name']
        labels = {
            'name': "Room Group Name"
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': "e.g. Jane_Doe's Room Group"
            }),
        }

    def __init__(self, *args, **kwargs):
        autofill_url = kwargs.pop('autofill_url', '')

        super().__init__(*args, **kwargs)

        if autofill_url:
            self.fields['search_name'].widget.attrs.update({'data-url': autofill_url})

    def clean_group_name(self):
        return self.cleaned_data['name'].strip()

    def clean_member_ids(self):

        data = self.cleaned_data['member_ids']

        if not data:
            raise forms.ValidationError("A Room Group must consist of at least one user.")

        try:
            return [int(x.strip()) for x in data.split(',') if x.strip().isdigit()]
        except ValueError:
            raise forms.ValidationError("Invalid user ID detected.")


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['building', 'floor', 'number', 'key', 'fob' , 'alarm', 'is_active', 'note']
        labels = {
            'number': 'Room Number',
            'key': 'Key?',
            'fob': 'FOB?',
            'alarm': 'Alarm?',
            'is_active': 'Active?',
        }
        widgets = {
            'building': forms.Select(attrs={ 'class': 'form-control' }),
            'floor': forms.Select(attrs={ 'class': 'form-control' }),
            'number': forms.TextInput(attrs={ 'class': 'form-control' }),
            'note': forms.Textarea(attrs={ 'class': 'form-control', 'rows': 6 })
        }
        help_texts = {
            'number': 'Maximum characters: 100'
        }
        error_messages = {
            'number': { 'required': 'Enter a valid number.' },
        }


KEY_REQUEST_LABELS = {
    'role': 'Applicant Role in LFS',
    'affiliation': 'Applicant UBC Affiliation',
    'employee_number': 'UBC Employee ID',
    'student_number': 'UBC Student Number',
    'supervisor_first_name': "Supervisor's First Name",
    'supervisor_last_name': "Supervisor's Last Name",
    'supervisor_email': "Supervisor's Email",
    'after_hours_access': 'After Hours Access',
    'working_alone': 'Working alone and/or in isolation',
    'comment': 'Additional Comments'
}


class KeyRequestForm(forms.ModelForm):
    class Meta:
        model = RequestForm
        exclude = ['rooms', 'submitted_at', 'updated_at']
        # fields = ['user', 'role', 'affiliation', 'employee_number', 'student_number', 'after_hours_access', 'working_alone', 'comment']

        labels = KEY_REQUEST_LABELS
        widgets = {
            'user': forms.HiddenInput(),
            'role': forms.TextInput(attrs={ 'class': 'form-control' }),
            'affiliation': forms.RadioSelect(),
            'employee_number': forms.TextInput(attrs={ 'class': 'form-control' }),
            'student_number': forms.TextInput(attrs={ 'class': 'form-control' }),
            'supervisor_first_name': forms.TextInput(attrs={ 'class': 'form-control' }),
            'supervisor_last_name': forms.TextInput(attrs={ 'class': 'form-control' }),
            'supervisor_email': forms.EmailInput(attrs={ 'class': 'form-control' }),
            'after_hours_access': forms.RadioSelect(),
            'comment': forms.Textarea(attrs={ 'class':'form-control', 'rows': 5 })
        }
        help_texts = {
            'role': 'Maximum characters: 100',
            'employee_number': 'Maximum characters: 7',
            'student_number': 'Maximum characters: 8',
            'supervisor_first_name': 'Maximum characters: 150',
            'supervisor_last_name': 'Maximum characters: 150',
            'supervisor_email': 'Maximum characters: 254',
            'after_hours_access': 'Regular building hours are from 7:30AM- 5PM Monday to Friday. If after hours access is required, please be sure to request entrance access.',
        }

    def clean(self):
        cleaned_data = super().clean()
        affl = cleaned_data.get('affiliation', None)
        empl = cleaned_data.get('employee_number', None)
        stud = cleaned_data.get('student_number', None)
        ahc = cleaned_data.get('after_hours_access', None)
        working_alone = cleaned_data.get('working_alone', None)

        if affl == '0' and not empl:
            raise ValidationError('<strong>UBC Employee ID</strong> is required when <strong>I have a UBC employee ID</strong> is selected. Please enter your <strong>UBC Employee ID</strong>, and then try again.')
        elif (affl == '1' or affl == '2') and not stud:
            raise ValidationError('<strong>UBC Student Number</strong> is required when <strong>I am an undergraduate/graduate student with a UBC student number</strong>. Please enter your <strong>UBC Student Number</strong>, and then try again.')
        
        if ahc == '0' and not working_alone:
            raise ValidationError('<strong>Working alone and/or in isolation</strong> is required when <strong>Yes, I will need after hours access</strong> is selected. Please check <strong>Working alone and/or in isolation</strong>, and then try again.')

