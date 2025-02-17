from binance.client import Client
from utils import config
from utils import utility, round_to
from enum import Enum
import logging
from datetime import datetime

from binance.websockets import BinanceSocketManager

import redis
import json

class BinanceStream(object):

  def __init__(self):
    self.client = Client(api_key=config.api_key, api_secret=config.api_secret)
    self.manager = BinanceSocketManager(self.client, user_timeout=30)
    self.user_socket = self.manager.start_user_socket(self.process_order)
    self.ticker_socket = self.manager.start_symbol_book_ticker_socket(config.symbol, self.process_tick)
    self.r = redis.Redis(host='localhost', port=6379, db=0)
    self.buy_orders = []
    self.sell_orders = []

  def process_order(self,msg):
    if msg['e'] == 'error':
      # close and restart the socket
      print("ERROR:", msg)
    else:
      print("message type: {}".format(msg['e']))

      if msg['e'] == 'executionReport' and msg['s'] == config.symbol :
        self.r.set(msg['c'], json.dumps(msg))
        print("Saved: ",msg)

  def process_tick(self,msg):
    if msg['s'] == config.symbol:
        name = 'bookTicker_' + msg['s']
        json_msg = json.dumps(msg)
        self.r.set(name, json_msg)
        self.r.xadd("stream_" + name, msg, maxlen=1000)
        print("Saved: ", json_msg)

  def start(self):
    self.manager.start()

  def stop(self):
    self.manager.close()


