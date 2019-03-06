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
11. To prepopulate db with certificates and labs run `./manage.py loaddata lfs_lab_cert_trackere/fixtures/*`

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

### Static Data

### Authentication
1. Use `python manage.py createsuperuser` to create a super user, just use something simple for development
2. Follow the prompts
3. Once completed login with the new admin user at `http://127.0.0.1/admin`
4. Once logged in create a group called "admin", "principal\_investigator", "student"
5. The "admin" group should be allowed all permissions
6. The "student" group should be allowed limited permissions TODO: Define these permissions
7. The "principal\_investigator" group should be allowed limited permissions TODO: Define these permissions

### Media Files
Create the directory `/srv/www/lfs-lab-cert-tracker` and ensure the Django process has read and write permissions
