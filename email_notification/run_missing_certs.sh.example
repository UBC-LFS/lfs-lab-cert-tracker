#!/bin/bash
LOGFILE=/[DIRECTORY]/trms/email_notification/cron.log

# source apache env
. /etc/apache2/envvars

echo "Run every 15 days - Started at $(date)" >> $LOGFILE 2>&1

/[DIRECTORY]/venv/bin/python3 /[DIRECTORY]/trms/email_notification/missing_certs.py >> $LOGFILE 2>&1