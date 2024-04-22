from django import forms
from django.contrib.auth.models import User as AuthUser
from lfs_lab_cert_tracker.models import Lab, Cert, UserLab, UserCert, LabCert, KeyRequest
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
        fields = ['name', 'expiry_in_years']
        labels = {
            'name': 'Training Name'
        }
        widgets = {
            'name': forms.TextInput(attrs={ 'class': 'form-control' }),
            'expiry_in_years': forms.TextInput(attrs={ 'class': 'form-control' })
        }
        help_texts = {
            'name': '(Maximum characters: 256)',
            'expiry_in_years': '(0 means "NO Expiry Date")'
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


# for testing

class DeleteUserCertForm(forms.Form):
    redirect_url = forms.CharField(widget=forms.HiddenInput())



class LabForm(forms.ModelForm):
    """ Create a new lab """

    redirect_url = forms.CharField(widget=forms.HiddenInput())
    class Meta:
        model = Lab
        fields = ['name', 'redirect_url']
        error_messages = {
            'name': { 'required': 'Enter a valid name.' },
        }

class LabCertForm(forms.ModelForm):
    """ Add a certificate to a lab """
    redirect_url = forms.CharField(widget=forms.HiddenInput())
    class Meta:
        model = LabCert
        fields = ['cert', 'redirect_url']
        labels = { 'cert': 'Training' }



class UserCertForm(forms.ModelForm):
    """ Add user's certificate """

    redirect_url = forms.CharField(widget=forms.HiddenInput())
    date = datetime.now()
    completion_date = forms.DateField(
        initial=dt.date.today,
        widget=forms.SelectDateWidget(years=range(date.year - 20, date.year + 20))
    )
    class Meta:
        model = UserCert
        fields = ['user', 'cert', 'cert_file', 'redirect_url']
        labels = {
            'cert': 'Training',
            'cert_file': ''
        }
        widgets = { 'user': forms.HiddenInput() }



class CertForm(forms.ModelForm):
    """ Create a certificate """

    redirect_url = forms.CharField(widget=forms.HiddenInput())
    class Meta:
        model = Cert
        fields = ['name', 'expiry_in_years', 'redirect_url']
        help_texts = { 'expiry_in_years': '(0 means "NO Expiry Date")' }
        error_messages = {
            'name': { 'required': 'Enter a valid name.' },
        }


class UserLabForm(forms.ModelForm):
    """ Add a user to a lab """

    class Meta:
        model = UserLab
        fields = ['user', 'role']
        labels = { 'user': 'CWL' }
        widgets = { 'user': forms.TextInput() }

class KeyRequestForm(forms.ModelForm):
    """ To request key access """
    class Meta:
        model = KeyRequest
        fields = ['firstName', 'lastName', 'cwl', 'ubcEmail', 'lfsRole', 'ubc_affiliation', 'supervisor_first_name', 'supervisor_last_name', 'supervisor_email', 'after_hours_access', 'building_name', 'room_numbers', 'additional_comments', 'requirement_to_proceed']

        labels = { 
            'firstName': 'First Name',
            'lastName': 'Last Name', 
            'cwl': 'UBC CWL User name', 
            'ubcEmail': 'Applicant UBC Email', 
            'lfsRole': 'Applicant Role in LFS', 
            'ubc_affiliation': 'Applicant UBC Affliation', 
            'building_name': 'Building Name'
        }

        help_texts = {
            'after_hours_access': 'Regular building hours are from 7:30AM- 5PM Monday to Friday. If after hours access is required, please be sure to request entrance access.',
            'building_name': 'This is the building you are requesting access to. We do not issue access to buildings not the list above. For Main and South Campus Greenhouses, contact UBC Plant Care Services plantcare.ubc.ca/contact-us',
            'room_numbers': 'A comma separated list. Use "entrance" for entrances. *** FNH 190 Pilot Plant Users *** Complete the FNH 190 Orientation and the code of conduct form before filling in this form.',
            'requirement_to_proceed': 'I understand this request will not be processed until all my required training certificates have been uploaded to https://training-report.landfood.ubc.ca. -- For undergraduate students who need access to FNH labs, please contact your supervisor.'
        }

        UBC_AFFILIATION_CHOICES = [
            ('employee', 'I have a UBC employee ID'),
            ('undergrad', 'I am an undergraduate student with a UBC student number'),
            ('grad', 'I am a graduate student with a UBC student number'),
            ('none', 'I do not have a UBC Card. Apply at ubccard.ubc.ca. Access cannot be granted without one.'),
        ]

        SUPERVISOR_BUILDING_CHOICES = [
            ('MCM', 'MCM'),
            ('FNH', 'FNH'),
            ('WESB', 'WESB'),
            ('UBC_Farm', 'UBC Farm'),
        ]

        AFTER_HOURS_ACCESS_CHOICES = [
            ('Yes', 'Yes, I will need after hours access'),
            ('No', 'No, I will not need after hours access')
        ]

        widgets = {
            "ubc_affiliation": forms.RadioSelect(choices=UBC_AFFILIATION_CHOICES),
            "after_hours_access": forms.RadioSelect(choices=SUPERVISOR_BUILDING_CHOICES),
            "building_name": forms.RadioSelect(choices=AFTER_HOURS_ACCESS_CHOICES),
            "additional_comments": forms.Textarea(attrs={"cols": 80, "rows": 20}),
            "requirement_to_proceed": forms.CheckboxInput(),  # Use CheckboxInput for BooleanField
        }

        additional_comments = forms.CharField(required=False, widget=forms.Textarea(attrs={"cols": 80, "rows": 20}))
