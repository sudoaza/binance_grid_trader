import time
import logging
from trader.binance_trader import BinanceTrader
from trader.binance_future_trader import BinanceFutureTrader
from utils import config

format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=format, filename='grid_trader_log.txt')
logger = logging.getLogger('binance')

if __name__ == '__main__':

    config.loads('./config.json')

    if config.platform == 'binance_spot':
        trader = BinanceTrader()
    else:
        trader = BinanceFutureTrader()
    #orders = trader.http_client.cancel_open_orders(config.symbol)
    #print(f"cancel orders: {orders}")

    while True:
        try:
            trader.grid_trader()
            time.sleep(10)

        except Exception as error:
            print(f"catch ERROR: {error}")
            print(error)
            time.sleep(20)

