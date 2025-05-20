from django import forms
from django.contrib.auth.models import User as AuthUser
from lfs_lab_cert_tracker.models import Lab, Cert, UserLab, UserCert, LabCert
from datetime import datetime
import datetime as dt

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

    """date = datetime.now()
    completion_date = forms.DateField(
        initial=dt.date.today,
        widget=forms.SelectDateWidget(years=range(date.year - 20, date.year + 20))
    )"""
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