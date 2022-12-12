from django import forms


class LocalLoginForm(forms.Form):
    username = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={ 
            'class': 'form-control',
            'placeholder': 'Enter'
        })
    )
    password = forms.CharField(
        max_length=200,
        widget=forms.PasswordInput(attrs={ 
            'class': 'form-control',
            'placeholder': 'Enter'
        })
    )
