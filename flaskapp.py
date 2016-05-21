from flask import Flask, request, redirect
from twilio.rest import TwilioRestClient
from googlefinance import getQuotes
from flask.ext.mysql import MySQL
import json
import requests
import os
import twilio.twiml
import unicodedata
import logging
logging.basicConfig(filename='/var/www/html/error.log',level=logging.DEBUG)
app = Flask(__name__)

  
@app.route('/messageHandler',methods=['GET', 'POST'])
def messageHandler():
  from_number = request.values.get('From', None)
  body = request.values.get('Body')
  body = body.strip().upper()
  bodyList = body.split(' ')
  
  if (bodyList[0] == "MORE"):
    retStr = moreInfo()
  elif (bodyList[0] == "SUBSCRIBE"):
    retStr = subscribeTicker(bodyList)
  elif (bodyList[0] == "UNSUBSCRIBE"):
    retStr = unsubscribeTicker(bodyList)
  else:
  	retStr = getPrice(bodyList)
  
  resp = twilio.twiml.Response()
  resp.message(retStr)
  return str(resp)
  
def moreInfo():
  return "more info of last looked up ticker"

def subscribeTicker(bodyList):
  return "Subscribe to ticker " + bodyList[1]
  
def unsubscribeTicker(bodyList):
  return "Unsubscribe to ticker " + bodyList[1]
  
def getPrice(bodyList):
  try:
    quote = getQuotes(str(bodyList[0]))
    price = quote[0]["LastTradePrice"]
  except:
    retStr = "ticker not found"
  else:
    retStr = bodyList[0] + " Price: " + price
  return retStr
  


if __name__ == '__main__':
  app.run(debug=True)