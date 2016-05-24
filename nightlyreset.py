from flask import Flask, request, redirect
from twilio.rest import TwilioRestClient
from yahoo_finance import Share
from flask.ext.mysql import MySQL
from datetime import datetime
import time
import json
import requests
import os
import twilio.twiml
import logging
from creds import *
logging.basicConfig(filename='/var/www/html/cron_error.log',level=logging.DEBUG)
app = Flask(__name__)
mysql = MySQL()

app.config['MYSQL_DATABASE_USER'] = DB_USER
app.config['MYSQL_DATABASE_PASSWORD'] = DB_PASSWORD
app.config['MYSQL_DATABASE_DB'] = DB_NAME
app.config['MYSQL_DATABASE_HOST'] = DB_HOST
app.config['MYSQL_DATABASE_PORT'] = DB_PORT

mysql.init_app(app)

#once a night at midnight we reset all the scheduled_sends to sent=0
#this sets them up to be sent out for the next day
conn = mysql.connect()
cur = conn.cursor()
q = '''UPDATE scheduled_sends SET sent = 0 WHERE active = 1'''
try:
    cur.execute(q)
    conn.commit()
except:
    conn.rollback()