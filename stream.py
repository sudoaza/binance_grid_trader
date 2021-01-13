import time
import logging
from trader.binance_stream import BinanceStream
from utils import config

format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=format, filename='grid_trader_log.txt')
logger = logging.getLogger('binance')

if __name__ == '__main__':

    config.loads('./config.json')
    stream = BinanceStream()
    stream.start()


