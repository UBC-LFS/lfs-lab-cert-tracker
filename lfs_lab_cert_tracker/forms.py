from django.forms import ModelForm, HiddenInput, FileInput, FileField, CharField

from lfs_lab_cert_tracker.models import (Lab, Cert, User,
        UserLab, UserCert, LabCert)

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

class LabCertForm(ModelForm):
    class Meta:
        model = LabCert
        fields = ['lab', 'cert']

class UserCertForm(ModelForm):
    redirect_url = CharField(widget=HiddenInput())
    class Meta:
        model = UserCert
        fields = ['user', 'cert', 'cert_file', 'redirect_url']
        widgets = {'user': HiddenInput()}

class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'cwl']
