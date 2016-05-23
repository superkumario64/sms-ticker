from flask import Flask, request, redirect
from twilio.rest import TwilioRestClient
from yahoo_finance import Share
from flask.ext.mysql import MySQL
from datetime import datetime
import json
import requests
import os
import twilio.twiml
import logging
logging.basicConfig(filename='/var/www/html/cron_error.log',level=logging.DEBUG)
app = Flask(__name__)

mysql = MySQL()

app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'root'
app.config['MYSQL_DATABASE_DB'] = 'sms_ticker'
app.config['MYSQL_DATABASE_HOST'] = '127.0.0.1'
app.config['MYSQL_DATABASE_PORT'] = 3306

mysql.init_app(app)

conn = mysql.connect()
cur = conn.cursor()
q = '''SELECT * FROM scheduled_sends WHERE sent = 0 AND active = 1'''
cur.execute(q)
rv = cur.fetchall()


print rv