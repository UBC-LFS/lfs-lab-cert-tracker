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
        error_messages = {
            'name': { 'required': 'Enter a valid name.' },
        }

class TrainingForm(forms.ModelForm):
    """ Create a certificate """

    class Meta:
        model = Cert
        fields = ['name', 'expiry_in_years']
        help_texts = {
            'name': '(Maximum characters: 256)',
            'expiry_in_years': '(0 means "NO Expiry Date")'
        }
        error_messages = {
            'name': { 'required': 'Enter a valid name.' },
        }

class TrainingNameForm(forms.ModelForm):
    class Meta:
        model = Cert
        fields = ['name']
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
            'user': forms.TextInput(),
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
        widgets = { 'lab': forms.HiddenInput() }


class UserTrainingForm(forms.ModelForm):
    """ Add user's training records """

    date = datetime.now()
    completion_date = forms.DateField(
        initial=dt.date.today,
        widget=forms.SelectDateWidget(years=range(date.year - 20, date.year + 20))
    )
    class Meta:
        model = UserCert
        fields = ['user', 'cert', 'cert_file']
        labels = {
            'cert': 'Training',
            'cert_file': ''
        }
        widgets = { 'user': forms.HiddenInput() }


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={ 'placeholder': 'Enter your username' })
    )
    password = forms.CharField(
        max_length=200,
        widget=forms.PasswordInput(attrs={ 'placeholder': 'Enter your password' })
    )

class SafetyWebForm(forms.Form):
    POSITION_CHOICES = (
        ('Volunteer', 'Volunteer'),
        ('Undergraduate', 'Undergraduate'),
        ('Visiting Faculty/Student', 'Visiting Faculty/Student'),
        ('Graduate Student', 'Graduate Student'),
        ('Postdoctoral Fellow', 'Postdoctoral Fellow'),
        ('Faculty Member', 'Faculty Member'),
        ('Laboratory Assistant', 'Laboratory Assistant'),
        ('Research Assistant', 'Research Assistant'),
        ('Lab Manager', 'Lab Manager'),
        ('Research Associate', 'Research Associate'),
    )

    HAZARDOUS_MTRLS_CHOICES = (
        ('Chemicals', 'Chemicals'),
        ('Animals', 'Animals'),
        ('Biologicals – RG1', 'Biologicals – RG1'),
        ('Biologicals – RG2', 'Biologicals – RG2'),
        ('Biologicals – Clinical specimens', 'Biologicals – Clinical specimens'),
        ('Radioisotopes', 'Radioisotopes'),
        ('Nanoparticles', 'Nanoparticles'),
    )

    EQUIPMENT_CHOICES = (
        ('Fume hood', 'Fume hood'),
        ('Biological Safety Cabinet', 'Biological Safety Cabinet'),
        ('Laminar Flow/Clean Air Bench', 'Laminar Flow/Clean Air Bench'),
        ('Liquid N2 Storage', 'Liquid N2 Storage'),
        ('UV transilluminator', 'UV transilluminator'),
        ('Dark room equipment', 'Dark room equipment'),
        ('Scintillation Counter', 'Scintillation Counter'),
        ('Fluorescence-Activated Cell Sorting', 'Fluorescence-Activated Cell Sorting'),
        ('Cell harvester', 'Cell harvester'),
        ('Autoclave', 'Autoclave'),
        ('Cryostat', 'Cryostat'),
        ('Centrifuge', 'Centrifuge'),
        ('Ultracentrifuge', 'Ultracentrifuge'),
        ('Electrophoresis', 'Electrophoresis'),
        ('LASERS', 'LASERS'),
        ('NMR', 'NMR'),
        ('Mass Spectrometer', 'Mass Spectrometer'),
        ('X-ray Generating Equipment', 'X-ray Generating Equipment'),
        ('Rotary Evaporators', 'Rotary Evaporators'),
        ('Lyophilizers (freeze dryers)', 'Lyophilizers (freeze dryers)'),
        ('Silicone baths', 'Silicone baths'),
        ('Sonicators', 'Sonicators'),
        ('Homogenizers/blenders', 'Homogenizers/blenders'),
        ('Compressed gas regulators', 'Compressed gas regulators'),
        ('Drying oven', 'Drying oven'),
        ('Muffle furnace', 'Muffle furnace'),
        ('Acid bath', 'Acid bath'),
        ('Distilled water unit', 'Distilled water unit'),
    )

    PPE_ABOVE_MIN_CHOICES = (
        ('Gloves', 'Gloves'),
        ('Face Shield', 'Face Shield'),
        ('Splash Goggles', 'Splash Goggles'),
        ('N95 Respirator', 'N95 Respirator'),
        ('Half-mask Respirator', 'Half-mask Respirator'),
    )

    redirect_url = forms.CharField(widget=forms.HiddenInput())
    name = forms.CharField()
    start_date = forms.DateField()
    end_date = forms.DateField()
    position = forms.ChoiceField(choices=POSITION_CHOICES)
    supervisor_name = forms.CharField()
    supervisor_phone_number = forms.CharField()
    supervisor_department = forms.CharField()
    supervisor_email = forms.EmailField()
    hazardous_materials = forms.MultipleChoiceField(choices=HAZARDOUS_MTRLS_CHOICES, widget=forms.CheckboxSelectMultiple)
    equipment = forms.MultipleChoiceField(choices=EQUIPMENT_CHOICES, widget=forms.CheckboxSelectMultiple)
    ppe_above_min = forms.MultipleChoiceField(choices=PPE_ABOVE_MIN_CHOICES, widget=forms.CheckboxSelectMultiple)


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
