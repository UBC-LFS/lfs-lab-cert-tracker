FROM python:3.6.7-slim

RUN apt-get update -y

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libxml2-dev \
        libxmlsec1-dev \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /app

COPY manage.py /app
COPY requirements.txt /app

RUN pip install -r /app/requirements.txt

RUN apt-get purge -y --auto-remove gcc

COPY lfs_lab_cert_tracker /app/lfs_lab_cert_tracker
COPY templates /app/templates

ENTRYPOINT cd /app; /usr/local/bin/gunicorn --bind 0.0.0.0:8080 lfs_lab_cert_tracker.wsgi:application
