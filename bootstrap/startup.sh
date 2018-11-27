#!/usr/bin/env bash

apt-get update
apt-get install -y python-pip \
                   python3-pip \
                   supervisor \
                   nginx \
                   postgresql \
                   postgresql-contrib

mkdir -p /var/log/lfs_lab_cert_tracker
mkdir -p /srv/www/lfs-lab-cert-tracker/media

if [ "$LFS_LAB_CERT_TRACKER_ENV" = "prod" ]; then
    git clone https://github.com/UBC-LFS/lfs-lab-cert-tracker.git
else
    ln -f -s /vagrant lfs-lab-cert-tracker
fi

pip3 install -r lfs-lab-cert-tracker/requirements.txt

# Copy over supervisord configurations
cp lfs-lab-cert-tracker/bootstrap/supervisord.conf /etc/supervisor/conf.d/lfs_lab_cert_tracker.conf

# Nginx setup
rm -f /etc/nginx/sites-enabled/default
cp lfs-lab-cert-tracker/bootstrap/nginx /etc/nginx/sites-available/lfs_lab_cert_tracker
ln -f -s /etc/nginx/sites-available/lfs_lab_cert_tracker /etc/nginx/sites-enabled/lfs_lab_cert_tracker

# Postgres setup
sudo -u postgres psql \
     -f lfs-lab-cert-tracker/bootstrap/setup_db.sql \
     -v POSTGRES_PASSWORD="'$LFS_LAB_CERT_TRACKER_DB_PASSWORD'" \
     postgres

$(cd lfs-lab-cert-tracker; python3 manage.py migrate)

# Add an admin
$(cd lfs-lab-cert-tracker; python3 manage.py create_app_superuser \
    --username="$APP_ADMIN_USERNAME" \
    --password="$APP_ADMIN_PASSWORD" \
    --email="$APP_ADMIN_EMAIL" \
    --noinput)

# Restart services
sudo service supervisor restart
sudo nginx -s reload
