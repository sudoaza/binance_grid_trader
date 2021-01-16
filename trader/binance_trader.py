from gateway import BinanceSpotHttp, OrderStatus, OrderType
from utils import config
from utils import utility, round_to
from enum import Enum
import logging
from datetime import datetime

class BinanceTrader(object):

    def __init__(self):
        """
        :param api_key:
        :param secret:
        :param trade_type: 交易的类型， only support future and spot.
        """
        self.http_client = BinanceSpotHttp(api_key=config.api_key, secret=config.api_secret)

        self.buy_orders = []
        self.sell_orders = []


    def get_bid_ask_price(self):
        ticker = self.http_client.get_ticker(config.symbol)
        bid_price = 0
        ask_price = 0
        if ticker:
            bid_price = float(ticker.get('bidPrice', 0))
            ask_price = float(ticker.get('askPrice', 0))

        return bid_price, ask_price

    def grid_trader(self):
        """
        :return:
        """

        self.bid_price, self.ask_price = self.get_bid_ask_price()
        self.avg_price = self.http_client.get_avg_price(config.symbol)

        print(f"bid_price: {self.bid_price}, ask_price: {self.ask_price}, avg_price: {self.avg_price}")

        self.buy_orders.sort(key=lambda x: float(x['price']), reverse=False)
        self.sell_orders.sort(key=lambda x: float(x['price']), reverse=True)
        print(f"buy orders: {self.buy_orders}")
        print("------------------------------")
        print(f"sell orders: {self.sell_orders}")

        delete_orders = []

        for order in (self.buy_orders + self.sell_orders):
            check_order = self.http_client.get_order(
                order.get('symbol', config.symbol),
                client_order_id=order.get('clientOrderId'))

            if check_order:
                if check_order.get('status') == OrderStatus.CANCELED.value:
                    delete_orders.append(order)
                    print(f"{order.get('side')} order CANCELLED {order.get('clientOrderId')}")

                elif check_order.get('status') == OrderStatus.FILLED.value:
                    logging.info(f"{order.get('side')} TX time: {datetime.now()}, price: {check_order.get('price')}, size: {check_order.get('origQty')}")
                    delete_orders.append(order)
                    self.place_order(self.avg_price)

                elif check_order.get('status') ==  OrderStatus.NEW.value:
                    print(f"{order.get('side')} order is NEW")

                else:
                    print(f"{order.get('side')}  order STATUS is NOT known: {check_order.get('status')}")

        for delete_order in delete_orders:
            if delete_order.get('side') == 'BUY':
                self.buy_orders.remove(delete_order)

            if delete_order.get('side') == 'SELL':
                self.sell_orders.remove(delete_order)

        if len(self.buy_orders) <= 0:
            if self.avg_price > 0:
                self.place_buy(self.avg_price)

        elif len(self.buy_orders) > int(config.max_orders):
            self.cancel('BUY')

        if len(self.sell_orders) <= 0:
            if self.avg_price > 0:
                self.place_sell(self.avg_price)

        elif len(self.sell_orders) > int(config.max_orders):
            self.cancel('SELL')

    def cancel(self, side):
        if side == 'BUY':
            orders = self.buy_orders
        elif side == 'SELL':
            orders = self.sell_orders

        delete_order = orders[0]
        order = self.http_client.cancel_order(delete_order.get('symbol'), client_order_id=delete_order.get('clientOrderId'))
        if order:
            orders.remove(delete_order)

    def price(self, last, side):
        gap = float(config.gap_percent)
        if side == 'BUY':
            gap = -gap
        elif side == 'SELL':
            pass
        else:
            print(f"ERROR {side} not BUY/SELL")
            return last

        price = round_to(float(last) * (1 + gap), float(config.min_price))

        if side == 'BUY':
            if price > self.bid_price > 0:
                price = round_to(self.bid_price, float(config.min_price))

        elif side == 'SELL':
            if 0 < price < self.ask_price:
                price = round_to(self.ask_price, float(config.min_price))
        
        return price

    def size(self):
        return round_to(float(config.quantity), float(config.min_qty))

    def create_order(self, side, price, size):
        print("size: ", size, "price: ", price)
        new_order = self.http_client.place_order(symbol=config.symbol, order_side=side, order_type=OrderType.LIMIT, quantity=size, price=price)
        if new_order:
            if side == 'SELL':
                self.sell_orders.append(new_order)
            elif side == 'BUY':
                self.buy_orders.append(new_order)

    def place_order(self, last_price):
        self.place_sell(last_price)
        self.place_buy(last_price)

    def place_sell(self, last_price):
        sell_price = self.price(last_price,'SELL')
        self.create_order('SELL', sell_price, self.size())

    def place_buy(self, last_price):
        buy_price = self.price(last_price,'BUY')
        self.create_order('BUY', buy_price, self.size())
