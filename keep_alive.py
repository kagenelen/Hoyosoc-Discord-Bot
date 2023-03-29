from flask import Flask
from threading import Thread
from datetime import datetime
import pytz
import logging

app = Flask('')

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app.logger.disabled = True
log.disabled = True


@app.route('/')
def home():
	tz_AU = pytz.timezone('Australia/Sydney') 
	datetime_AU = datetime.now(tz_AU)
	return "Genshin helper online at " + datetime_AU.strftime("%H:%M:%S")


def run():
  app.run(host='0.0.0.0', port=8080)


def keep_alive():
  t = Thread(target=run)
  t.start()
