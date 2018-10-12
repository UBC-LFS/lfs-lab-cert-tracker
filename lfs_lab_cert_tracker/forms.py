from django.forms import ModelForm, ModelMultipleChoiceField

from lfs_lab_cert_tracker.models import Lab, Cert, User, UserLab

class LabForm(ModelForm):
    class Meta:
        model = Lab
        fields = ['name']

class CertForm(ModelForm):
    class Meta:
        model = Cert
        fields = ['name']

class UserLabForm(ModelForm):
    class Meta:
        model = UserLab
        fields = ['user', 'lab', 'role']

class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'cwl']
