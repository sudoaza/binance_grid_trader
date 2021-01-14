import requests
import time
import hmac
import hashlib
from enum import Enum
from threading import Lock
import redis
import json


class OrderStatus(Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    PENDING_CANCEL = "PENDING_CANCEL"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP = "STOP"


class Interval(Enum):
    MINUTE_1 = '1m'
    MINUTE_3 = '3m'
    MINUTE_5 = '5m'
    MINUTE_15 = '15m'
    MINUTE_30 = '30m'
    HOUR_1 = '1h'
    HOUR_2 = '2h'
    HOUR_4 = '4h'
    HOUR_6 = '6h'
    HOUR_8 = '8h'
    HOUR_12 = '12h'
    DAY_1 = '1d'
    DAY_3 = '3d'
    WEEK_1 = '1w'
    MONTH_1 = '1M'

class BinanceSpotHttp(object):

    def __init__(self, api_key=None, secret=None, host=None, timeout=5, try_counts=1):
        self.api_key = api_key
        self.secret = secret
        self.host = host if host else "https://api.binance.com"
        self.recv_window = 10000
        self.timeout = timeout
        self.order_count_lock = Lock()
        self.order_count = 1_000_000
        self.try_counts = try_counts # failed attempts
        self.r = redis.Redis(host='localhost', port=6379, db=0)

    def cache(self, key):
        try:
            cache = self.r.get(key)
            if cache is not None:
                cache = json.loads(cache.decode('utf-8'))
            
            return cache
        except Exception as error:
            print("ERROR: ", error)
            return

    def build_parameters(self, params: dict):
        keys = list(params.keys())
        keys.sort()
        return '&'.join([f"{key}={params[key]}" for key in params.keys()])

    def request(self, req_method: str, path: str, requery_dict=None, verify=False):
        url = self.host + path

        if verify:
            query_str = self._sign(requery_dict)
            url += '?' + query_str
        elif requery_dict:
            url += '?' + self.build_parameters(requery_dict)
        headers = {"X-MBX-APIKEY": self.api_key}

        for i in range(0, self.try_counts):
            try:
                response = requests.request(req_method, url=url, headers=headers, timeout=self.timeout)
                if response.status_code == 200:
                    return response.json()
                else:
                    print("===###///  WARN  ///###===")
                    print(response.json(), response.status_code)
            except Exception as error:
                print("===###///  FAILURE  ///###===")
                print(f"req: {path}, err: {error}")
                # time.sleep(3)

    def get_ticker(self, symbol: str):
        ticker = self.get_ticker_from_cache(symbol)
        if ticker is None:
            ticker = self.get_ticker_from_api(symbol)

        return ticker

    def get_ticker_from_cache(self, symbol: str):
        cache = self.cache('bookTicker_' + symbol)
        if cache is not None:
            # Websocket and HTTP api have different field names
            cache = {
                'symbol': cache['s'],
                'bidPrice': cache['b'],
                'bidQty': cache['B'],
                'askPrice': cache['a'],
                'askQty': cache['A']
                }
        return cache

    def get_ticker_from_api(self, symbol: str):
        """
        :param symbol
        :return:
        {
        'symbol': 'BTCUSDT', 'bidPrice': '9168.50000000', 'bidQty': '1.27689900',
        'askPrice': '9168.51000000', 'askQty': '0.93307800'
        }
        """
        path = "/api/v3/ticker/bookTicker"
        query_dict = {"symbol": symbol}
        return self.request('GET', path, query_dict)

    def get_client_order_id(self):
        """
        generate the client_order_id for user.
        :return:
        """
        with self.order_count_lock:
            self.order_count += 1
            return "x-AZA737" + str(self.get_current_timestamp()) + str(self.order_count)

    def get_current_timestamp(self):
        return int(time.time() * 1000)

    def _sign(self, params):
        """
        signature for the private request.
        :param params: request parameters
        :return:
        """
        query_string = self.build_parameters(params)
        hex_digest = hmac.new(self.secret.encode('utf8'), query_string.encode("utf-8"), hashlib.sha256).hexdigest()
        return query_string + '&signature=' + str(hex_digest)

    def place_order(self, symbol: str, order_side: str, order_type: OrderType, quantity: float, price: float,
                    client_order_id: str = None, time_inforce="GTC", stop_price=0):
        """
        :param symbol: 交易对名称
        :param order_side: 买或者卖， BUY or SELL
        :param order_type: 订单类型 LIMIT or other order type.
        :param quantity: 数量
        :param price: 价格.
        :param client_order_id: 用户的订单ID
        :param time_inforce:
        :param stop_price:
        :return:
        """

        path = '/api/v3/order'

        if client_order_id is None:
            client_order_id = self.get_client_order_id()

        params = {
            "symbol": symbol,
            "side": order_side,
            "type": order_type.value,
            "quantity": quantity,
            "price": price,
            "recvWindow": self.recv_window,
            "timestamp": self.get_current_timestamp(),
            "newClientOrderId": client_order_id
        }

        if order_type == OrderType.LIMIT:
            params['timeInForce'] = time_inforce

        if order_type == OrderType.MARKET:
            if params.get('price'):
                del params['price']

        if order_type == OrderType.STOP:
            if stop_price > 0:
                params["stopPrice"] = stop_price
            else:
                raise ValueError("stopPrice must greater than 0")

        return self.request('POST', path=path, requery_dict=params, verify=True)

    def get_order(self, symbol: str, client_order_id: str):
        order = self.get_order_from_cache(client_order_id)
        if order is None:
            order = self.get_order_from_api(symbol, client_order_id)

        return order

    def get_order_from_cache(self, client_order_id: str):
        cache = self.cache(client_order_id)
        if cache is not None:
            cache = {
                'clientOrderId': cache['c'],
                'origQty': cache['q'],
                'price': cache['p'],
                'status': cache['X']
                }
        return cache
    
    def get_order_from_api(self, symbol: str, client_order_id: str):
        path = "/api/v3/order"
        prams = {"symbol": symbol, "timestamp": self.get_current_timestamp(), "origClientOrderId": client_order_id}

        return self.request('GET', path, prams, verify=True)

    def cancel_order(self, symbol, client_order_id):
        """
        :param symbol:
        :param client_order_id:
        :return:
        """
        path = "/api/v3/order"
        params = {"symbol": symbol, "timestamp": self.get_current_timestamp(),
                  "origClientOrderId": client_order_id
                  }

        for i in range(0, 3):
            try:
                order = self.request('DELETE', path, params, verify=True)
                return order
            except Exception as error:
                print(f'cancel order error:{error}')
        return

    def get_open_orders(self, symbol=None):
        """
        :param symbol: BNBUSDT, or BTCUSDT etc.
        :return:
        """
        path = "/api/v3/openOrders"

        params = {"timestamp": self.get_current_timestamp()}
        if symbol:
            params["symbol"] = symbol

        return self.request('GET', path, params, verify=True)

    def cancel_open_orders(self, symbol):
        """
        :param symbol: symbol
        :return: return a list of orders.
        """
        path = "/api/v3/openOrders"

        params = {"timestamp": self.get_current_timestamp(),
                  "recvWindow": self.recv_window,
                  "symbol": symbol
                  }

        return self.request('DELETE', path, params, verify=True)

    def get_account_info(self):
        """
        {'feeTier': 2, 'canTrade': True, 'canDeposit': True, 'canWithdraw': True, 'updateTime': 0, 'totalInitialMargin': '0.00000000',
        'totalMaintMargin': '0.00000000', 'totalWalletBalance': '530.21334791', 'totalUnrealizedProfit': '0.00000000',
        'totalMarginBalance': '530.21334791', 'totalPositionInitialMargin': '0.00000000', 'totalOpenOrderInitialMargin': '0.00000000',
        'maxWithdrawAmount': '530.2133479100000', 'assets':
        [{'asset': 'USDT', 'walletBalance': '530.21334791', 'unrealizedProfit': '0.00000000', 'marginBalance': '530.21334791',
        'maintMargin': '0.00000000', 'initialMargin': '0.00000000', 'positionInitialMargin': '0.00000000', 'openOrderInitialMargin': '0.00000000',
        'maxWithdrawAmount': '530.2133479100000'}]}
        :return:
        """
        path = "/api/v3/account"
        params = {"timestamp": self.get_current_timestamp(),
                  "recvWindow": self.recv_window
                  }
        return self.request('GET', path, params, verify=True)

