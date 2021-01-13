#  51bitquant网格交易策略

# Config

```json
{
  "platform": "binance_spot",  
  "symbol": "BTCUSDT",
  "api_key": "replace your api key here",
  "api_secret": "replace your api secret here",
  "gap_percent": 0.001,
  "quantity": 0.001,
  "min_price": 0.01,
  "min_qty": 0.001,
  "max_orders": 1,
  "proxy_host": "127.0.0.1",
  "proxy_port": 1087
}

```

1. platform: trading platform binance_spot or binance_future
2. symbol 交易对: BTCUSDT, BNBUSDT等
3. api_key : 从交易所获取
4. api_secret: 交易所获取
5. gap_percent: gap between orders 
6. quantity : order quantity
7. min_price: min price unit fraction   
8. min_qty: min tradable quantity
9. max_orders: 单边的下单量
10. proxy_host: 如果需要用代理的话，请填写你的代理 your proxy host, if you
    want proxy
11. proxy_port: 代理端口号 your proxy port for connecting to binance.


## Start

** Deletes all market orders on start!! **

> sh start.sh 

