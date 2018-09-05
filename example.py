from time import sleep
from bittrex_websocket import OrderBook
import requests
import json
import sys


market_url = "https://bittrex.com/api/v1.1/public/getmarkets"


class MyOrderBook(OrderBook):
    def __init__(self, tickers):
        super().__init__()
        self.enable_log()
        self.subscribe_to_orderbook(tickers)


def get_json_from_url(url):
    try:
        response = requests.get(url)
        content = response.content.decode("utf8")
        js = json.loads(content)
        return js
    except Exception as ex:
        print(get_json_from_url.__name__, ex)


def get_markets():
    try:
        result = get_json_from_url(market_url)
        if result['success']:
            markets = result['result']
            rs = {}
            for market in markets:
                base_currency = market['BaseCurrency']
                market_currency = market['MarketCurrency']
                # market_name = market['MarketName']
                active = market['IsActive']
                if active:
                    if base_currency not in rs:
                        rs[base_currency] = []
                    else:
                        rs[base_currency].append(market_currency)
            # print(json.dumps(rs))
            return rs
    except Exception as ex:
        print(ex)


def find_triangular(markets, base_currency: list=['USD', 'USDT', 'BTC']):
    # for m in markets:
    #     print(m)
    triangulars = []
    for m in markets:
        if m in base_currency:
            for c1 in markets[m]:
                # print(c)
                if c1 in markets:
                    for c2 in markets[c1]:
                        if c2 in markets[m]:
                            triangulars.append([m, c1, c2])
    return triangulars


def find_market_to_watch(triangulars):
    market_names = []
    for t in triangulars:
        market_name = '{0}-{1}'.format(t[0], t[1])
        if market_name not in market_names:
            market_names.append(market_name)
        market_name = '{0}-{1}'.format(t[1], t[2])
        if market_name not in market_names:
            market_names.append(market_name)
        market_name = '{0}-{1}'.format(t[0], t[2])
        if market_name not in market_names:
            market_names.append(market_name)
    return market_names


def find_diff(triangulars, ob: MyOrderBook):
    tickers = find_market_to_watch(triangulars)
    orderbooks = {}
    fee = 0.0025
    for ticker in tickers:
        orderbooks[ticker] = ob.get_order_book(ticker)
    for triangular in triangulars:
        pair1 = '{0}-{1}'.format(triangular[0], triangular[1])
        pair2 = '{0}-{1}'.format(triangular[1], triangular[2])
        pair3 = '{0}-{1}'.format(triangular[0], triangular[2])
        if not orderbooks[pair1] or not orderbooks[pair2] or not orderbooks[pair3]:
            continue
        pair1_buy_price = orderbooks[pair1]['Z'][0]['R']
        pair1_buy_quantity = orderbooks[pair1]['Z'][0]['Q']
        pair2_buy_price = orderbooks[pair2]['Z'][0]['R']
        pair2_buy_quantity = orderbooks[pair2]['Z'][0]['Q']
        pair3_buy_price = orderbooks[pair3]['Z'][0]['R']
        pair3_buy_quantity = orderbooks[pair3]['Z'][0]['Q']
        pair1_sell_price = orderbooks[pair1]['S'][0]['R']
        pair1_sell_quantity = orderbooks[pair1]['S'][0]['Q']
        pair2_sell_price = orderbooks[pair2]['S'][0]['R']
        pair2_sell_quantity = orderbooks[pair2]['S'][0]['Q']
        pair3_sell_price = orderbooks[pair3]['S'][0]['R']
        pair3_sell_quantity = orderbooks[pair3]['S'][0]['Q']

        # buy buy sell
        currency1 = 1
        currency2 = (currency1 - currency1 * fee) / pair1_sell_price
        currency3 = (currency2 - currency2 * fee) / pair2_sell_price
        currency = (currency3 - currency3 * fee) * pair3_buy_price
        if currency - currency1 > 0:

            print(triangular, 'buy->buy->sell')
            print(currency-currency1)
        # buy sell sell
        currency1 = 1
        currency3 = (currency1 - currency1 * fee) / pair3_sell_price
        currency2 = (currency3 - currency3 * fee) * pair2_buy_price
        currency = (currency2 - currency2 * fee) * pair1_buy_price
        if currency - currency1 > 0:
            print(triangular, 'sell->sell->buy')
            print(currency-currency1)
        # sys.stdout.write('.')
        # sys.stdout.flush()


if __name__ == "__main__":
    # main()
    market = get_markets()
    triangulars = find_triangular(market, ['USD', 'USDT', 'BTC'])
    print(triangulars)
    tickers = find_market_to_watch(triangulars)
    ob = MyOrderBook(tickers=tickers)
    while True:
        sleep(1)
        find_diff(triangulars, ob)
        sys.stdout.write('.')
        sys.stdout.flush()
        # book = ob.get_order_book('USDT-ETH')
        # print(json.dumps(book))

