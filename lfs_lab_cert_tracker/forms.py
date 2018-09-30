from django.forms import ModelForm

from lfs_lab_cert_tracker.models import Lab, Cert

class LabForm(ModelForm):
    class Meta:
        model = Lab
        fields = ['name']

class CertForm(ModelForm):
    class Meta:
        model = Cert
        fields = ['name']
