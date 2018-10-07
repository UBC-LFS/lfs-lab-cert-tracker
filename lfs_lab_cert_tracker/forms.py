from django.forms import ModelForm, ModelMultipleChoiceField

from django.contrib.auth.models import User
from lfs_lab_cert_tracker.models import Lab, Cert, User, UserLab

class LabForm(ModelForm):
    class Meta:
        model = Lab
        fields = ['name']

class CertForm(ModelForm):
    class Meta:
        model = Cert
        fields = ['name']

class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ['id']

class UserLabForm(ModelForm):
    class Meta:
        model = UserLab
        fields = ['user_id', 'lab_id', 'role']
