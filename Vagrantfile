# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # Use a ubuntu 16.04 box
  config.vm.box = "ubuntu/xenial64"

  config.vm.network "forwarded_port", guest: 80, host: 8080, host_ip: "127.0.0.1"

  config.vm.provision "shell", inline: <<-SHELL
    apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        software-properties-common

    # Install docker
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -

    # TODO: Add check to verify fingerprint

    add-apt-repository -y \
        "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) \
        stable"
    apt-get update
    apt-get install -y docker-ce

    export LFS_LAB_CERT_TRACKER_DB_PASSWORD=dummy_password
    export LFS_LAB_CERT_TRACKER_ENV=dev
    export APP_ADMIN_USERNAME=admin
    export APP_ADMIN_PASSWORD=admin123!
    export APP_ADMIN_EMAIL=admin@foobar.com
    /vagrant/bootstrap/startup.sh
  SHELL
end
