CREATE DATABASE lfs_lab_cert_tracker;
CREATE USER lfs_lab_cert_tracker_user WITH PASSWORD 'dummy_password';
ALTER ROLE lfs_lab_cert_tracker_user SET client_encoding TO 'utf8';
ALTER ROLE lfs_lab_cert_tracker_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE lfs_lab_cert_tracker_user SET timezone TO 'UTC';
