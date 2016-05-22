from flask import Flask, request, redirect
from twilio.rest import TwilioRestClient
from googlefinance import getQuotes
from yahoo_finance import Share
from flask.ext.mysql import MySQL
import json
import requests
import os
import twilio.twiml
import unicodedata
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
        retStr = subscribeTicker(bodyList)
    elif (bodyList[0] == "UNSUBSCRIBE"):
        retStr = unsubscribeTicker(bodyList)
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
    try:
        quote = Share(str(rv[1]))
        prevClose = quote.get_prev_close()
        openPrice = quote.get_open()
        volume = quote.get_volume()
        logging.debug(quote)
    except:
        retStr = "ticker not found"
    else:
        retStr = "PrevClose: "+prevClose+" OpenPrice: "+openPrice+" Volume: "+ volume
    
    return retStr

def subscribeTicker(bodyList):
    return "Subscribe to ticker " + bodyList[1]

def unsubscribeTicker(bodyList):
    return "Unsubscribe to ticker " + bodyList[1]

def getPrice(bodyList, from_number):
    try:
        quote = getQuotes(str(bodyList[0]))
        price = quote[0]["LastTradePrice"]
    except:
        retStr = "ticker not found"
    else:
        retStr = bodyList[0] + " Price: " + price

    conn = mysql.connect()
    cur = conn.cursor()
    q = '''INSERT INTO last_lookup (phone, ticker)
               VALUES (%s, %s)
               ON DUPLICATE KEY UPDATE
               ticker = VALUES(ticker)
        '''
    try:
        cur.execute(q,(from_number,bodyList[0]))
        conn.commit()
    except:
        conn.rollback()

    return retStr


def getTickerPrice(ticker):
    try:
        quote = getQuotes(str(ticker))
        price = quote[0]["LastTradePrice"]
    except:
        retStr = "ticker not found"
    else:
        retStr = ticker + " Price: " + price
    return retStr


if __name__ == '__main__':
    app.run(debug=True)