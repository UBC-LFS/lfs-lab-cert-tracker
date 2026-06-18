from django import forms
from django.core.exceptions import ValidationError

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
    'after_hours_access': 'After Hours Access',
    'working_alone': 'Working alone and/or in isolation',
    'comment': 'Additional Comments'
}


def get_room_managers():
    manager_set = set()
    for room in Room.objects.all():
        for m in room.managers.all():
            manager_set.add((int(m.id), m.get_full_name()))
    
    manager_sorted = sorted(manager_set, key=lambda x: x[1])
    managers = list(manager_sorted)
    managers.insert(0, ('', 'Select'))
    return managers
        

class KeyRequestForm(forms.ModelForm):
    supervisor = forms.ChoiceField(
        required=True,
        label='Supervisor',
        choices=get_room_managers(),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = RequestForm
        exclude = ['rooms', 'submitted_at', 'updated_at']
        labels = KEY_REQUEST_LABELS
        widgets = {
            'user': forms.HiddenInput(),
            'role': forms.TextInput(attrs={ 'class': 'form-control' }),
            'affiliation': forms.RadioSelect(),
            'employee_number': forms.TextInput(attrs={ 'class': 'form-control' }),
            'student_number': forms.TextInput(attrs={ 'class': 'form-control' }),
            'after_hours_access': forms.RadioSelect(),
            'comment': forms.Textarea(attrs={ 'class':'form-control', 'rows': 5 })
        }
        help_texts = {
            'role': 'Maximum characters: 100',
            'employee_number': 'Maximum characters: 7',
            'student_number': 'Maximum characters: 8',
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

