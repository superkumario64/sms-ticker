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


#This cron job runs every minute and sends emails at an appropriate time


#This is the same getPrice fxn from flaskapp.py
#I am still looking into how to make this more DRY and only live in one place
def getPrice(bodyList, from_number):
    retStr = ""
    #interate over bodyList
    for ticker in bodyList:
        quote = Share(str(ticker))
        price = quote.get_price()
        #construct return string with price ticker if found
        #appended the comma and space in the front, will remove preceeding comma after loop
        if price:
            retStr += ", " + ticker + " Price: " + price
        else:
            retStr += ", ticker not found"
        
        #update last_lookup field so the "more info" feature works
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
    
    #strip preceeding comma and space
    retStr = retStr[2:]
    return retStr

#query to find any scheduled sends that are active and have not been sent today
conn = mysql.connect()
cur = conn.cursor()
q = '''SELECT * FROM scheduled_sends WHERE sent = 0 AND active = 1'''
cur.execute(q)
rv = cur.fetchall()

for row in rv:
    #construct a datetime object from the DB row to be used in compare against sys datetime
    msgDateStr = time.strftime("%m/%d/%Y")
    msgDateStr += " " + row[2]
    msgDateObj = datetime.strptime(msgDateStr,"%m/%d/%Y %I:%M%p")
    now = datetime.now()
    # if the server time is >= the time in the DB row
    if now >= msgDateObj:
        #send the sms with the price of the ticker in DB row
        client = TwilioRestClient(account_sid, auth_token)
        msgBody = getPrice([row[1]], row[0])
        message = client.messages.create(to=rv[0], from_="+18312001157", body=msgBody)
        conn = mysql.connect()
        cur = conn.cursor()
        #update DB row to sent=1 so we do not resend to this user the next time the cron runs
        q = '''UPDATE scheduled_sends SET sent = 1 WHERE phone = %s AND ticker = %s AND send_time = %s'''
        try: 
            cur.execute(q,(row[0],row[1],row[2]))
            conn.commit()
        except:
            conn.rollback()