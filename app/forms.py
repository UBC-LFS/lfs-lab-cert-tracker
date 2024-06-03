from django import forms
from django.contrib.auth.models import User as AuthUser
from lfs_lab_cert_tracker.models import *


class UserForm(forms.ModelForm):
    """ Create a new user """

    class Meta:
        model = AuthUser
        fields = ['username', 'first_name', 'last_name', 'email']
        labels = {
            'username': 'CWL',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email'
        }
        help_texts = {
            'username': 'Unique. Maximum 150 characters allowed',
            'first_name': 'Maximum 30 characters allowed',
            'last_name': 'Maximum 150 characters allowed',
            'email': 'Maximum 254 characters allowed'
        }
        error_messages = {
            'username': { 'required': 'Enter a valid username.' },
        }
        widgets = {
            'first_name': forms.TextInput(attrs={
                'required': True,
                'class': 'form-control',
                'placeholder': 'Enter'
             }),
            'last_name': forms.TextInput(attrs={
                'required': True,
                'class': 'form-control',
                'placeholder': 'Enter'
            }),
            'email': forms.EmailInput(attrs={
                'required': True,
                'class': 'form-control',
                'placeholder': 'Enter'
            }),
            'username': forms.TextInput(attrs={
                'required': True,
                'class': 'form-control',
                'placeholder': 'Enter'
            })
        }

class AreaForm(forms.ModelForm):
    """ Create a new lab """

    class Meta:
        model = Lab
        fields = ['name']
        labels = {
            'name': 'Area Name'
        }
        widgets = {
            'name': forms.TextInput(attrs={ 'class': 'form-control' })
        }
        help_texts = {
            'name': '(Maximum characters: 256)'
        }
        error_messages = {
            'name': { 'required': 'Enter a valid name.' },
        }

class TrainingForm(forms.ModelForm):
    """ Create a certificate """

    def clean_expiry_in_years(self):
        expiry_in_years = self.cleaned_data['expiry_in_years']
        if expiry_in_years < 0:
            raise forms.ValidationError("Expiry in years cannot be less than 0")
        return expiry_in_years

    class Meta:
        model = Cert
        fields = ['name', 'expiry_in_years', 'unique_id']
        labels = {
            'name': 'Training Name',
            'expiry_in_years': 'Expiry in Years',
            'unique_id': 'Training Unique ID'
        }
        widgets = {
            'name': forms.TextInput(attrs={ 'class': 'form-control' }),
            'expiry_in_years': forms.TextInput(attrs={ 'class': 'form-control' }),
            'unique_id': forms.TextInput(attrs={ 'class': 'form-control' })
        }
        help_texts = {
            'name': '(Maximum characters: 256)',
            'expiry_in_years': '(0 means "NO Expiry Date")',
            'unique_id': 'Note: Each training has an unique ID in Canvas Catalog'
        }
        error_messages = {
            'name': { 'required': 'Enter a valid name.' },
        }


class UserAreaForm(forms.ModelForm):
    ''' Add a user to an area '''

    class Meta:
        model = UserLab
        fields = ['user', 'lab', 'role']
        labels = { 'user': 'CWL' }
        widgets = {
            'user': forms.TextInput(attrs={ 'class': 'form-control' }),
            'role': forms.Select(attrs={ 'class': 'form-control' }),
            'lab': forms.HiddenInput()
        }


class UserAreaSimpleForm(forms.ModelForm):
    ''' Add a user to an area '''

    class Meta:
        model = UserLab
        fields = ['user', 'lab']
        widgets = {
            'user': forms.HiddenInput(),
            'lab': forms.HiddenInput()
        }
        error_messages = {
            'user': { 'required': 'This field is required' },
            'lab': { 'required': 'This field is required' }
        }


class AreaTrainingForm(forms.ModelForm):
    ''' Add a training to an area '''

    class Meta:
        model = LabCert
        fields = ['lab', 'cert']
        labels = { 'cert': 'Training' }
        widgets = { 
            'cert': forms.Select(attrs={ 'class': 'form-control' }),
            'lab': forms.HiddenInput() 
        }


class UserTrainingForm(forms.ModelForm):
    """ Add user's training records """

    class Meta:
        model = UserCert
        fields = ['user', 'cert', 'cert_file', 'completion_date']
        labels = {
            'cert': 'Training',
            'cert_file': 'Certificate File',
            'completion_date': 'Completion Date'
        }
        widgets = {
            'user': forms.HiddenInput(),
            'cert': forms.Select(attrs={ 'class': 'form-control' }),
            'completion_date': forms.widgets.DateInput(attrs={ 'type': 'date', 'class': 'form-control' }),
        }


class AccessRequestForm(forms.ModelForm):    
    class Meta:
        model = AccessRequest
        exclude = ['created_at', 'updated_at']
        labels = {
            'role': 'Applicant Role in LFS',
            'affliation': 'Applicant UBC Affliation',
            'employee_number': 'UBC Employee ID',
            'student_number': 'UBC Student Number',
            'supervisor_first_name': "Supervisor's First Name",
            'supervisor_last_name': "Supervisor's Last Name",
            'supervisor_email': "Supervisor's Email",
            'after_hours_access': 'After hours access',
            'working_alone': 'Working alone and/or in isolation',
            'building_name': 'Building Name',
            'room_numbers': 'Room Numbers that I need access to',
            'comment': 'Additional Comments'
        }
        widgets = {
            'user': forms.HiddenInput(),
            'lab': forms.HiddenInput(),
            'role': forms.TextInput(attrs={ 'class': 'form-control-sm' }),
            'affliation': forms.RadioSelect(),
            'employee_number': forms.TextInput(attrs={ 'class': 'form-control-sm' }),
            'student_number': forms.TextInput(attrs={ 'class': 'form-control-sm' }),
            'supervisor_first_name': forms.TextInput(attrs={ 'class': 'form-control-sm' }),
            'supervisor_last_name': forms.TextInput(attrs={ 'class': 'form-control-sm' }),
            'supervisor_email': forms.TextInput(attrs={ 'class': 'form-control-sm' }),
            'after_hours_access': forms.RadioSelect(),
            'building_name': forms.RadioSelect(),
            'room_numbers': forms.TextInput(attrs={ 'class': 'form-control-sm' }),
            'comment': forms.Textarea(attrs={ 'class':'form-control-sm', 'rows': 3 })
        }
        help_texts = {
            'employee_number': 'Maximum characters: 7',
            'student_number': 'Maximum characters: 8',
            'after_hours_access': 'Regular building hours are from 7:30AM- 5PM Monday to Friday. If after hours access is required, please be sure to request entrance access.',
            'building_name': 'This is the building you are requesting access to. We do not issue access to buildings not the list above. For Main and South Campus Greenhouses, contact UBC Plant Care Services plantcare.ubc.ca/contact-us',
            'room_numbers': 'A comma separated list. Use "entrance" for entrances. *** FNH 190 Pilot Plant Users *** Complete the FNH 190 Orientation and the code of conduct form before filling in this form.',
            

        }
