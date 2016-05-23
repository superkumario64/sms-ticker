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
logging.basicConfig(filename='/var/www/html/error.log',level=logging.DEBUG)
app = Flask(__name__)
mysql = MySQL()

app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'root'
app.config['MYSQL_DATABASE_DB'] = 'sms_ticker'
app.config['MYSQL_DATABASE_HOST'] = '127.0.0.1'
app.config['MYSQL_DATABASE_PORT'] = 3306

mysql.init_app(app)
  
@app.route('/messageHandler',methods=['GET', 'POST'])
def messageHandler():
    from_number = request.values.get('From', None)
    body = request.values.get('Body')
    body = body.strip().upper()
    bodyList = body.split(' ')

    if (bodyList[0] == "MORE"):
        retStr = moreInfo(from_number)
    elif (bodyList[0] == "SUBSCRIBE"):
        retStr = subscribeTicker(bodyList, from_number)
    elif (bodyList[0] == "UNSUBSCRIBE"):
        retStr = unsubscribeTicker(bodyList, from_number)
    else:
        retStr = getPrice(bodyList, from_number)

    resp = twilio.twiml.Response()
    resp.message(retStr)
    return str(resp)

def moreInfo(from_number):
    conn = mysql.connect()
    cur = conn.cursor()
    q = '''SELECT * FROM last_lookup WHERE phone = %s'''
    cur.execute(q,[from_number])
    rv = cur.fetchone()
    quote = Share(str(rv[1]))
    prevClose = quote.get_prev_close()
    openPrice = quote.get_open()
    volume = quote.get_volume()
    logging.debug(quote)
    if prevClose:
        retStr = "PrevClose: "+prevClose+" OpenPrice: "+openPrice+" Volume: "+ volume
    else:
        retStr = "ticker still not found"
    
    return retStr

def subscribeTicker(bodyList, from_number):
    try:
        ticker = bodyList[1]
    except IndexError:
        return "please specify ticker symbol"
    quote = Share(str(ticker))
    price = quote.get_price()
    if price:
        try:
            send_time = bodyList[2]
        except IndexError:
            send_time = "8:30AM"
        try:
            datetime.strptime(send_time, '%I:%M%p')
            conn = mysql.connect()
            cur = conn.cursor()
            q = '''INSERT INTO scheduled_sends (phone, ticker, send_time)
                       VALUES(%s, %s, %s)
                '''
            try:
                cur.execute(q,(from_number,ticker,send_time))
                conn.commit()
                return "Successfully subscribed to " + ticker + " at " + send_time
            except:
                conn.rollback()
                return "mysql error"
        except ValueError:
                return "please enter a valid time HH:MM{AM/PM}"
    
    return "could not find ticker"

def unsubscribeTicker(bodyList, from_number):
    try:
        ticker = bodyList[1]
    except IndexError:
        return "please specify ticker symbol to unsubscribe. Use 'unsubscribe everything' remove all subscriptions"
    if ticker == 'EVERYTHING':
        conn = mysql.connect()
        cur = conn.cursor()
        q = '''UPDATE scheduled_sends SET active = 0 WHERE phone = %s'''
        try:
            cur.execute(q,[from_number])
            conn.commit()
            return "Successfully unsubscribed to everything"
        except:
            conn.rollback()
            return "mysql error"
    else:
        conn = mysql.connect()
        cur = conn.cursor()
        q = '''UPDATE scheduled_sends SET active = 0 WHERE phone = %s AND ticker = %s'''
        try:
            cur.execute(q,[from_number, ticker])
            conn.commit()
            return "Successfully unsubscribed to " + ticker
        except:
            conn.rollback()
            return "mysql error"

def getPrice(bodyList, from_number):
    retStr = ""
    for ticker in bodyList:
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

if __name__ == '__main__':
    app.run(debug=True)