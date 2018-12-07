FROM python:3.6.7-slim

RUN mkdir /app

COPY manage.py /app
COPY requirements.txt /app
RUN pip install -r /app/requirements.txt

COPY lfs_lab_cert_tracker /app/lfs_lab_cert_tracker
COPY templates /app/templates

ENTRYPOINT cd /app; /usr/local/bin/gunicorn --bind 0.0.0.0:8080 lfs_lab_cert_tracker.wsgi:application
