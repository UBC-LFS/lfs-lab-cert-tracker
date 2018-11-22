FROM python:3.6.7-slim

RUN mkdir /app

ADD manage.py /app
ADD requirements.txt /app
RUN pip install -r /app/requirements.txt

ADD lfs_lab_cert_tracker /app/lfs_lab_cert_tracker
ADD templates /app/templates

ENTRYPOINT cd /app; gunicorn --bind 0.0.0.0:8000 lfs_lab_cert_tracker.wsgi:application
