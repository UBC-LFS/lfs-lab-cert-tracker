#!/usr/bin/env bash

apt-get update
apt-get install -y python-pip \
                   python3-pip \
                   supervisor \
                   nginx \
                   postgresql \
                   postgresql-contrib

# Create logging directory
mkdir -p /var/log/lfs_lab_cert_tracker
# Create media directory for serving files
mkdir -p /srv/www/lfs-lab-cert-tracker/media

# Whether we are working in a vagrant box or production box
if [ "$LFS_LAB_CERT_TRACKER_ENV" = "prod" ]; then
    git clone https://github.com/UBC-LFS/lfs-lab-cert-tracker.git
else
    ln -f -s /vagrant lfs-lab-cert-tracker
fi

pip3 install -r lfs-lab-cert-tracker/requirements.txt

# Link the supervisord conf
ln -r -f -s lfs-lab-cert-tracker/bootstrap/supervisord.conf /etc/supervisor/conf.d/lfs_lab_cert_tracker.conf

# Nginx setup
rm -f /etc/nginx/sites-enabled/default


# Link the Nginx configs
ln -r -f -s lfs-lab-cert-tracker/bootstrap/nginx /etc/nginx/sites-available/lfs_lab_cert_tracker
ln -f -s /etc/nginx/sites-available/lfs_lab_cert_tracker /etc/nginx/sites-enabled/lfs_lab_cert_tracker

# Postgres setup
sudo -u postgres psql \
     -f lfs-lab-cert-tracker/bootstrap/setup_db.sql \
     -v POSTGRES_PASSWORD="'$LFS_LAB_CERT_TRACKER_DB_PASSWORD'" \
     postgres

echo $(cd lfs-lab-cert-tracker; python3 manage.py migrate)

# Add an admin
echo $(cd lfs-lab-cert-tracker; python3 manage.py create_app_superuser \
    --username="$APP_ADMIN_USERNAME" \
    --password="$APP_ADMIN_PASSWORD" \
    --email="$APP_ADMIN_EMAIL" \
    --noinput)

# Restart services
sudo service supervisor restart
sudo nginx -s reload
