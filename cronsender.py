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
logging.basicConfig(filename='/var/www/html/cron_error.log',level=logging.DEBUG)
app = Flask(__name__)
mysql = MySQL()

app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'root'
app.config['MYSQL_DATABASE_DB'] = 'sms_ticker'
app.config['MYSQL_DATABASE_HOST'] = '127.0.0.1'
app.config['MYSQL_DATABASE_PORT'] = 3306
account_sid = "AC427ba42c195ad5c939af0b8b92a6fd28"
auth_token = "ab9c7fbcb552d6d06ba14f58585680dd"


mysql.init_app(app)

def getPrice(bodyList, from_number):
    retStr = ""
    for ticker in bodyList:
        print ticker
        print from_number
        quote = Share(str(ticker))
        price = quote.get_price()
        if price:
            retStr += ", " + ticker + " Price: " + price
        else:
            retStr += ", ticker not found"
        
        conn = mysql.connect()
        cur = conn.cursor()
        q = '''INSERT INTO last_lookup (phone, ticker)
                   VALUES (%s, %s)
                   ON DUPLICATE KEY UPDATE
                   ticker = VALUES(ticker)
            '''
        try:
            cur.execute(q,(from_number,ticker))
            conn.commit()
        except:
            conn.rollback()
    retStr = retStr[2:]
    return retStr

conn = mysql.connect()
cur = conn.cursor()
q = '''SELECT * FROM scheduled_sends WHERE sent = 0 AND active = 1'''
cur.execute(q)
rv = cur.fetchall()
for row in rv:
    msgDateStr = time.strftime("%m/%d/%Y")
    msgDateStr += " " + row[2]
    msgDateObj = datetime.strptime(msgDateStr,"%m/%d/%Y %I:%M%p")
    now = datetime.now()
    if now >= msgDateObj:
        client = TwilioRestClient(account_sid, auth_token)
        msgBody = getPrice([row[1]], row[0])
        message = client.messages.create(to=rv[0], from_="+18312001157", body=msgBody)
        conn = mysql.connect()
        cur = conn.cursor()
        q = '''UPDATE scheduled_sends SET sent = 1 WHERE phone = %s AND ticker = %s AND send_time = %s'''
        try: 
            cur.execute(q,(row[0],row[1],row[2]))
            conn.commit()
        except:
            conn.rollback()
#print rv