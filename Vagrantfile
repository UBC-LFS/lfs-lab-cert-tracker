# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # Use a ubuntu 16.04 box
  config.vm.box = "ubuntu/xenial64"

  config.vm.network "forwarded_port", guest: 80, host: 8080, host_ip: "127.0.0.1"

  config.vm.provision "shell", inline: <<-SHELL
    apt-get update
    apt-get install -y python-pip
    apt-get install -y python3-pip
    apt-get install -y supervisor
    apt-get install -y nginx
    apt-get install -y postgresql postgresql-contrib
    mkdir -p /var/log/lfs_lab_cert_tracker
    mkdir -p /srv/www/lfs-lab-cert-tracker
    pip3 install -r /vagrant/requirements.txt
    cp /vagrant/bootstrap/supervisord.conf /etc/supervisor/conf.d/lfs_lab_cert_tracker.conf
    cp /vagrant/bootstrap/nginx /etc/nginx/sites-available/lfs_lab_cert_tracker
    rm /etc/nginx/sites-enabled/default
    ln -s /etc/nginx/sites-available/lfs_lab_cert_tracker /etc/nginx/sites-enabled/lfs_lab_cert_tracker

    sudo -u postgres psql -f /vagrant/bootstrap/setup_db.sql postgres
    sudo service supervisor restart
    sudo nginx -s reload
  SHELL
end
