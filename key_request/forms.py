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
            'name': 'Maximum characters: 50'
        }


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['building', 'floor', 'number']
        labels = {
            'number': 'Room Number'
        }
        widgets = {
            'building': forms.Select(attrs={ 'class': 'form-control' }),
            'floor': forms.Select(attrs={ 'class': 'form-control' }),
            'number': forms.TextInput(attrs={ 'class': 'form-control' })
            
        }
        help_texts = {
            'number': 'It must be unique. Maximum characters: 10'
        }
        error_messages = {
            'number': { 'required': 'Enter a valid number.' },
        }

KEY_REQUEST_LABELS = {
    'role': 'Applicant Role in LFS',
    'affliation': 'Applicant UBC Affliation',
    'employee_number': 'UBC Employee ID',
    'student_number': 'UBC Student Number',
    'supervisor_first_name': "Supervisor's First Name",
    'supervisor_last_name': "Supervisor's Last Name",
    'supervisor_email': "Supervisor's Email",
    'after_hours_access': 'After Hours Access',
    'working_alone': 'Working alone and/or in isolation',
    'comment': 'Additional Comments'            
    # 'building_name': 'Building Name',
    # 'room_numbers': 'Room Numbers that I need access to',
}

class KeyRequestForm(forms.ModelForm):
    class Meta:
        model = RequestForm
        exclude = ['rooms', 'submitted_at', 'updated_at']
        # fields = ['user', 'role', 'affliation', 'employee_number', 'student_number', 'after_hours_access', 'working_alone', 'comment']

        labels = KEY_REQUEST_LABELS
        widgets = {
            'user': forms.HiddenInput(),
            'role': forms.TextInput(attrs={ 'class': 'form-control' }),
            'affliation': forms.RadioSelect(),
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
        affl = cleaned_data.get('affliation', None)
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

