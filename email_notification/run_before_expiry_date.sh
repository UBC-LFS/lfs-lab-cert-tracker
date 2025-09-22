#!/bin/bash
LOGFILE=/[DIRECTORY]/trms/email_notification/cron.log

. /etc/apache2/envvars

echo "Run everyday - Started at $(date)" >> $LOGFILE 2>&1

/[DIRECTORY]/venv/bin/python3 /[DIRECTORY]/trms/email_notification/before_expiry_date.py >> $LOGFILE 2>&1