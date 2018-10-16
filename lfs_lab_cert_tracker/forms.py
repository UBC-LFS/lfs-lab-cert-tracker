from django.forms import ModelForm, HiddenInput, FileInput, FileField, CharField

from lfs_lab_cert_tracker.models import (Lab, Cert, User,
        UserLab, UserCert, LabCert)

class LabForm(ModelForm):
    redirect_url = CharField(widget=HiddenInput())
    class Meta:
        model = Lab
        fields = ['name', 'redirect_url']

class CertForm(ModelForm):
    redirect_url = CharField(widget=HiddenInput())
    class Meta:
        model = Cert
        fields = ['name', 'redirect_url']

class UserLabForm(ModelForm):
    redirect_url = CharField(widget=HiddenInput())
    class Meta:
        model = UserLab
        fields = ['user', 'lab', 'role', 'redirect_url']

class LabCertForm(ModelForm):
    redirect_url = CharField(widget=HiddenInput())
    class Meta:
        model = LabCert
        fields = ['lab', 'cert', 'redirect_url']

class UserCertForm(ModelForm):
    redirect_url = CharField(widget=HiddenInput())
    class Meta:
        model = UserCert
        fields = ['user', 'cert', 'cert_file', 'redirect_url']
        widgets = {'user': HiddenInput()}

class UserForm(ModelForm):
    redirect_url = CharField(widget=HiddenInput())
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'cwl', 'redirect_url']
