# Project Goals
A Django site that allows for user profiles, containing a user's certification and training records.

Records will be used for determining access to labs and fulfill Worksafe BC requirements.

# Dev (Local VM)
Run `vagrant up` that should create a VM which runs this as a container.

# Dev
## Python Environment
1. Use pyenv-virtualenv to create a virtual environment for development
2. Run `pyenv virtualenv 3.6.6 lfs-lab-cert-tracker` to create a virtual environment. If you don't have python3.6.6 installed, install it first with `pyenv install 3.6.6`
3. Enter the virtual environment with `pyenv activate lfs-lab-cert-tracker` exit it with `source deactivate`
4. Making sure you're in the virtualenv run `pip install -r requirements.txt` to get all the packages for this project
5. If shibboleth authenticator fails try `brew install libxml2-dev libxmlsec1-dev`

## Local Database
This project uses Postgresql as its database, follow these instructions to get it running locally DON'T USE THESE STEPS IN PROD
### OSX
1. Install postgresql with `brew install postgresql`
2. Run postgresql as background service with `brew services start postgresql`
3. Enter sql prompt with `psql postgres`
4. To create a database for this project run `CREATE DATABASE lfs_lab_cert_tracker;`
5. To create a database user for this project run `CREATE USER lfs_lab_cert_tracker_user WITH PASSWORD 'dummy_password';`
6. Run the following commands to ensure the postgres database is configured to what Django expects
```
ALTER ROLE lfs_lab_cert_tracker_user SET client_encoding TO 'utf8';
ALTER ROLE lfs_lab_cert_tracker_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE lfs_lab_cert_tracker_user SET timezone TO 'UTC';
```
7. To give full access of this database to the Django user run `GRANT ALL PRIVILEGES ON DATABASE lfs_lab_cert_tracker TO lfs_lab_cert_tracker_user;`
8. Exit the sql prompt with `\q`
9. To see if local db setup worked run `python manage.py makemigrations` if that worked then db setup was a success
10. Then run `python manage.py migrate` to complete setting up the database
11. To prepopulate db with certificates and labs run `./manage.py loaddata lfs_lab_cert_tracker/fixtures/*`

### Admin Setup
1. Run
```
./manage.py create_app_superuser \
	--username=<admim username> \
	--password=<admin password> \
	--email=<admin email> \
	--first_name=<admin first name> \
	--last_name=<admin last name> \
	--cwl=<admin cwl> \
	--database=default \
	--noinput
```

or

1. Run

```
# Reference: https://docs.djangoproject.com/en/2.2/topics/auth/default/
$ python manage.py createsuperuser --username=joe --email=joe@example.com
```

2. Login with this URL: `http://localhost:8000/accounts/admin/login/`

### Authentication
1. Use `python manage.py createsuperuser` to create a super user, just use something simple for development
2. Follow the prompts
3. Once completed login with the new admin user at `http://127.0.0.1/admin`
4. Once logged in create a group called "admin", "principal\_investigator", "student"
5. The "admin" group should be allowed all permissions
6. The "student" group should be allowed limited permissions TODO: Define these permissions
7. The "principal\_investigator" group should be allowed limited permissions TODO: Define these permissions


### SAML
- To login with SAML `http://<url>/accounts/login`

### Without SAML

- To login without using SAML head to `http://localhost:8000/my_login/` for local login and testing


### Media Files
Create the directory `/srv/www/lfs-lab-cert-tracker` and ensure the Django process has read and write permissions

## Deploying to Alpine 3.9
1. Install these prerequisites
```
apk add postgresql-dev
apk add gcc
apk add libxml2-dev
apk add libxslt-dev
apk add libc-dev
apk add python3-dev
apk add xmlsec-dev
apk add pkgconfig
```

2. To run as a service copy the file `scripts/cert-tracker` and place in `/etc/init.d`
3. To start run `service cert-tracker start`
4. To stop run `service cert-tracker stop`
5. stdout and stderr are redirected to logfiles in `/var/log/cert-tracker`

## Troubleshooting
* Error
```
import xmlsec
SystemError: null argument to internal routine
```
Solution
If running inside alpine and not running verison 3.9 update to 3.9



## Summary of Deployment

1. Clone this Github repository
```
$ git clone https://github.com/UBC-LFS/lfs-lab-cert-tracker.git
```

2. Install requirement dependencies
```
$ pip install -r requirements.txt
```

3. Set Environment Variables in your machine:
```
SECRET_KEY = os.environ['CERT_TRACKER_SECRET_KEY']
DATABASE_ENGINE = os.environ['LFS_LAB_CERT_TRACKER_DB_ENGINE']
DATABASE = os.environ['LFS_LAB_CERT_TRACKER_DB_NAME']
USER = os.environ['LFS_LAB_CERT_TRACKER_DB_USER']
PASSWORD = os.environ['LFS_LAB_CERT_TRACKER_DB_PASSWORD']
HOST = os.environ['LFS_LAB_CERT_TRACKER_DB_HOST']
PORT = os.environ['LFS_LAB_CERT_TRACKER_DB_PORT']
EMAIL_HOST = os.environ['LFS_LAB_CERT_TRACKER_EMAIL_HOST']
EMAIL_FROM = os.environ['LFS_LAB_CERT_TRACKER_EMAIL_FROM']

# Environment variables for sending reminder emails
LFS_LAB_CERT_TRACKER_URL = os.environ['LFS_LAB_CERT_TRACKER_URL']
```

4. Switch *DEBUG* to **False** in a *settings.py* file
```
DEBUG = False
```

5. Add a Media root directory to store certificate files
```
MEDIA_ROOT = 'your_media_root'
```

6. Add your allowed_hosts in *settings.py*
```
ALLOWED_HOSTS = ['YOUR_HOST']
```

7. Create staticfiles in your directory
```
$ python manage.py collectstatic --noinput

# References
# https://docs.djangoproject.com/en/2.2/howto/static-files/
# https://devcenter.heroku.com/articles/django-assets
# https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django/Deployment
```

8. Create a database in Postgresql

9. Create database tables, and migrate
```
$ python manage.py makemigrations
$ python manage.py migrate
```

10. Add valid certificate information
```
$ python manage.py loaddata certs
```

11. Update *settings.json* and *advanced_settings.json* files in the **saml** folder

12. See a deployment checklist and change your settings
```
$ python manage.py check --deploy


# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/
# CSRF_COOKIE_SECURE = True
# SESSION_COOKIE_SECURE = True
# SECURE_BROWSER_XSS_FILTER = True
# SECURE_CONTENT_TYPE_NOSNIFF = True
# SECURE_SSL_REDIRECT = True
# X_FRAME_OPTIONS = 'DENY'
```



13. Test this Django application and an email notification system
```
# Django app
$ python manage.py test lfs_lab_cert_tracker

# email notification
$ python email_notification/test.py
```

14. Uncomment a **local_login** path for local running routes.

```
# urls.py
path('accounts/local_login/', views.local_login, name='local_login')


```

15. Now, it's good to go. Run this web application in your production!
```
$ python manage.py runserver

For scheduling tasks
$ python manage.py runserver --noreload
```

16. Test
```
# Users
$ python manage.py test lfs_lab_cert_tracker.tests.users

# Email notification
$ python manage.py test lfs_lab_cert_tracker.tests.notifications
```

Happy coding!
