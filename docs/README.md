# Description of files
```
lfs_lab_cert_tracker
├── api.py -> Interface to the application Models
├── api_views.py -> Provides web facing access to internal API
├── auth_utils.py -> Functions for authenticating
├── fixtures -> Prepopulated data
│   ├── certificates.json
│   ├── lab_certs.json
│   └── labs.json
├── forms.py -> Contains Django Forms
├── management (dir) -> Helper app commands
├── migrations (dir) -> Migration history
├── models.py -> Models for application
├── redirect_utils.py -> Used in api_views to redirect
├── settings.py
├── urls.py -> Paths used in this application
├── views.py -> Handles frontend
└── wsgi.py
```
