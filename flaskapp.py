from flask import Flask, request, redirect
from twilio.rest import TwilioRestClient
from yahoo_finance import Share
from flask.ext.mysql import MySQL
from datetime import datetime
from creds import *
import json
import requests
import os
import twilio.twiml
import logging
logging.basicConfig(filename='/var/www/html/error.log',level=logging.DEBUG)
app = Flask(__name__)
mysql = MySQL()

app.config['MYSQL_DATABASE_USER'] = DB_USER
app.config['MYSQL_DATABASE_PASSWORD'] = DB_PASSWORD
app.config['MYSQL_DATABASE_DB'] = DB_NAME
app.config['MYSQL_DATABASE_HOST'] = DB_HOST
app.config['MYSQL_DATABASE_PORT'] = DB_PORT

mysql.init_app(app)
  
#this is the route that is setup at the twilio webhook
#it splits up the body of the sms and calls the appropriate function
@app.route('/messageHandler',methods=['POST'])
def messageHandler():
    #grab the number the incoming sms in coming from
    from_number = request.values.get('From', None)
    #grab the body of incoming sms, convert to upper case 
    #and split the string into a list words
    body = request.values.get('Body')
    body = body.strip().upper()
    bodyList = body.split()

    #this if/elif drives the main 4 functions this sms app can do
    #
    #if the user sends 'more info'
    if (len(bodyList) > 1 and bodyList[0] == "MORE" and bodyList[1] == "INFO"):
        logging.debug("more info block")
        retStr = moreInfo(from_number)
    #if the first word is Subscribe attempt to subscribe user to daily stock quotes
    elif (bodyList[0] == "SUBSCRIBE"):
        retStr = subscribeTicker(bodyList, from_number)
    #if the first word is unsubscribe attempt to unsubscribe the user appropriately
    elif (bodyList[0] == "UNSUBSCRIBE"):
        retStr = unsubscribeTicker(bodyList, from_number)
    #else we attempt to get a price quote for each ticker in the list
    else:
        retStr = getPrice(bodyList, from_number)

    #after we are done processing the users sms
    #we respond back with an appropriate message
    resp = twilio.twiml.Response()
    resp.message(retStr)
    return str(resp)

#if the user inputs 'more info' we lookup the last ticker
#that a user used in a price lookup and send the user more info on that ticker
def moreInfo(from_number):
    #query to find the stock the user last looked up
    conn = mysql.connect()
    cur = conn.cursor()
    q = '''SELECT * FROM last_lookup WHERE phone = %s'''
    cur.execute(q,[from_number])
    rv = cur.fetchone()
    
    #get stock information
    quote = Share(str(rv[1]))
    prevClose = quote.get_prev_close()
    openPrice = quote.get_open()
    volume = quote.get_volume()
    
    #if we get all the information back respond back with more info
    if prevClose and openPrice and volume:
        retStr = "PrevClose: "+prevClose+" OpenPrice: "+openPrice+" Volume: "+ volume
    #else the user has not looked up a stock yet
    else:
        retStr = "ticker still not found"
    
    return retStr

#The subscribe method can be used by just hitting 'subscribe {ticker}'
#it can also take an optional time argument after the ticker symbol
#if no time is provided it defaults to 8:30AM Pacific Time
#time form is %I:%M%p eg 10:30AM
#(all times are pacific time)
def subscribeTicker(bodyList, from_number):
    #first check to see if the user put in a second word for the ticker
    try:
        ticker = bodyList[1]
    except IndexError:
        return "please specify ticker symbol"
    #lookup stock price    
    quote = Share(str(ticker))
    price = quote.get_price()
    #if we found a price, the ticker does exist
    if price:
        #determine send time (either user input or default to 8:30AM)
        try:
            send_time = bodyList[2]
        except IndexError:
            send_time = "8:30AM"
        
        try:
            #validate date input
            datetime.strptime(send_time, '%I:%M%p')
            
            #insert into schduled sends table
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
                return "You may already be subscribed to "  + ticker + " at " + send_time
        #if date value not formatted correctly
        except ValueError:
                return "please enter a valid time HH:MM{AM/PM}"
    #return ticker not found if price is not found
    return "could not find ticker"

#The unsubscribe feature can be used 'unsubscribe {ticker}' to unsubscribe to all of your subscriptions to that ticker
#you can also hit 'unsubscribe everything' to unsubscribe to all of your subscriptions
def unsubscribeTicker(bodyList, from_number):
    #check to make sure there is a second argument
    try:
        ticker = bodyList[1]
    except IndexError:
        return "please specify ticker symbol to unsubscribe. Use 'unsubscribe everything' remove all subscriptions"
    
    if ticker == 'EVERYTHING':
        conn = mysql.connect()
        cur = conn.cursor()
        #update all of that users rows in the scheduled_sends table
        #the user will no longer have any active subscriptions
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
        #only update users subscriptions to a specific stock ticker
        q = '''UPDATE scheduled_sends SET active = 0 WHERE phone = %s AND ticker = %s'''
        try:
            cur.execute(q,[from_number, ticker])
            conn.commit()
            return "Successfully unsubscribed to " + ticker
        except:
            conn.rollback()
            return "mysql error"

#loops through and gets the prices of all the tickers provided
#the last ticker to be looked up will the the ticker used in the more feature
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

if __name__ == '__main__':
    app.run(debug=True)