from django import forms

from lfs_lab_cert_tracker.models import (Lab, Cert, User,
        UserLab, UserCert, LabCert)

class LabForm(forms.ModelForm):
    redirect_url = forms.CharField(widget=forms.HiddenInput())
    class Meta:
        model = Lab
        fields = ['name', 'redirect_url']

class CertForm(forms.ModelForm):
    redirect_url = forms.CharField(widget=forms.HiddenInput())
    class Meta:
        model = Cert
        fields = ['name', 'redirect_url']

class UserLabForm(forms.ModelForm):
    redirect_url = forms.CharField(widget=forms.HiddenInput())
    class Meta:
        model = UserLab
        fields = ['user', 'lab', 'role', 'redirect_url']

class LabCertForm(forms.ModelForm):
    redirect_url = forms.CharField(widget=forms.HiddenInput())
    class Meta:
        model = LabCert
        fields = ['lab', 'cert', 'redirect_url']

class UserCertForm(forms.ModelForm):
    redirect_url = forms.CharField(widget=forms.HiddenInput())
    class Meta:
        model = UserCert
        fields = ['user', 'cert', 'cert_file', 'redirect_url']
        widgets = {'user': forms.HiddenInput()}

class DeleteUserCertForm(forms.Form):
    redirect_url = forms.CharField(widget=forms.HiddenInput())

class UserForm(forms.ModelForm):
    redirect_url = forms.CharField(widget=forms.HiddenInput())
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'cwl', 'redirect_url']

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

