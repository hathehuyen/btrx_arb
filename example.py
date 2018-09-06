from time import sleep
from bittrex_websocket import OrderBook
from bittrex_api import BittrexAPI
import requests
import json
import sys
import settings


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
                # min_trade_size = market['MinTradeSize']
                active = market['IsActive']
                if active:
                    if base_currency not in rs:
                        rs[base_currency] = []
                    else:
                        rs[base_currency].append(market_currency)

            # print(json.dumps(rs))
            return rs, markets
        return False, False
    except Exception as ex:
        print(ex)
        return False, False


def find_triangular(markets, base_currency: list=['USD', 'USDT', 'BTC']):
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
    fee = settings.fee
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
        if currency - currency1 > settings.min_profit_pct:
            print(triangular, 'buy->buy->sell')
            print(currency-currency1)
            return 'buy-buy-sell', triangular, [pair1_sell_price, pair2_sell_price, pair3_buy_price], \
                   [pair1_sell_quantity, pair2_sell_quantity, pair3_buy_quantity]
        # buy sell sell
        currency1 = 1
        currency3 = (currency1 - currency1 * fee) / pair3_sell_price
        currency2 = (currency3 - currency3 * fee) * pair2_buy_price
        currency = (currency2 - currency2 * fee) * pair1_buy_price
        if currency - currency1 > settings.min_profit_pct:
            print(triangular, 'buy->sell->sell')
            print(currency-currency1)
            return 'buy-sell-sell', triangular, [pair1_sell_price, pair2_buy_price, pair3_buy_price], \
                   [pair1_sell_quantity, pair2_buy_quantity, pair3_buy_quantity]
        # sys.stdout.write('.')
        # sys.stdout.flush()
    return False, False, False, False


def find_balance(balances, currency):
    for balance in balances:
        if balance['Currency'] == currency:
            return balance['Available']
    return 0


def check_min_size(markets, triangular, quantities):
    currency1 = triangular[0]
    currency2 = triangular[1]
    currency3 = triangular[2]
    quantity_pair1 = quantities[0]
    quantity_pair2 = quantities[1]
    quantity_pair3 = quantities[2]
    pair1 = '{0}-{1}'.format(currency1, currency2)
    pair2 = '{0}-{1}'.format(currency2, currency3)
    pair3 = '{0}-{1}'.format(currency1, currency3)
    for market in markets:
        if market['MarketName'] == pair1 and market['MinTradeSize'] < quantity_pair1:
            return False
        if market['MarketName'] == pair2 and market['MinTradeSize'] < quantity_pair2:
            return False
        if market['MarketName'] == 3 and market['MinTradeSize'] < quantity_pair3:
            return False
    return True


def main_loop():
    market, market_raw = get_markets()
    triangulars = find_triangular(market, ['BTC'])
    # print(triangulars)
    tickers = find_market_to_watch(triangulars)
    ob = MyOrderBook(tickers=tickers)
    bittrex_api = BittrexAPI(settings.api_key, settings.api_secret)
    balances = bittrex_api.getbalances()

    while True:
        sleep(1)
        order, triangular, prices, quantities = find_diff(triangulars, ob)
        if order:
            currency1 = triangular[0]
            currency2 = triangular[1]
            currency3 = triangular[2]
            price_pair1 = prices[0]
            price_pair2 = prices[1]
            price_pair3 = prices[2]
            quantity_pair1 = quantities[0]
            quantity_pair2 = quantities[1]
            quantity_pair3 = quantities[2]
            balance_currency1 = find_balance(balances, currency1)
            print('{0} balance: {1}'.format(currency1, balance_currency1))
            if order == 'buy-buy-sell':
                balance_currency2 = (balance_currency1 - balance_currency1 * settings.fee) / price_pair1
                if balance_currency2 > quantity_pair1:
                    balance_currency2 = quantity_pair1
                else:
                    quantity_pair1 = balance_currency2
                balance_currency3 = (balance_currency2 - balance_currency2 * settings.fee) / price_pair2

                if balance_currency3 > quantity_pair2:
                    balance_currency3 = quantity_pair2
                    balance_currency2 = balance_currency3 * price_pair2
                    balance_currency2 += balance_currency2 * settings.fee
                    quantity_pair1 = balance_currency2
                else:
                    quantity_pair2 = balance_currency3

                if quantity_pair3 < balance_currency3:
                    balance_currency3 = quantity_pair3
                    quantity_pair2 = balance_currency3
                    quantity_pair1 = quantity_pair2 * price_pair2
                else:
                    quantity_pair3 = balance_currency3

                if not check_min_size(market_raw, triangular, [quantity_pair1, quantity_pair2, quantity_pair3]):
                    print('Size too small')
                    continue
                if price_pair1 * quantity_pair1 < 0.0011:
                    print('Min trade requirement not meet (< 0.0011)')
                    continue

                print('buy {0}-{1}, price {2}, quantity {3}'.format(currency1, currency2, price_pair1, quantity_pair1))
                rs = bittrex_api.buylimit('{0}-{1}'.format(currency1, currency2), quantity_pair1, price_pair1)
                print(rs)

                balances = bittrex_api.getbalances()
                balance_currency2 = find_balance(balances, currency2)
                quantity_pair2 = (balance_currency2 - balance_currency2 * settings.fee ) / price_pair2
                print('buy {0}-{1}, price {2}, quantity {3}'.format(currency2, currency3, price_pair2, quantity_pair2))
                rs = bittrex_api.buylimit('{0}-{1}'.format(currency2, currency3), quantity_pair2, price_pair2)
                print(rs)

                balances = bittrex_api.getbalances()
                quantity_pair3 = find_balance(balances, currency3)
                print('sell {0}-{1}, price {2}, quantity {3}'.format(currency1, currency3, price_pair3, quantity_pair3))
                rs = bittrex_api.selllimit('{0}-{1}'.format(currency1, currency3), quantity_pair3, price_pair3)
                print(rs)

            if order == 'buy-sell-sell':
                if quantity_pair3 * price_pair3 > balance_currency1 - balance_currency1 * settings.fee:
                    quantity_pair3 = (balance_currency1 - balance_currency1 * settings.fee) / price_pair3
                balance_currency3 = quantity_pair3

                if quantity_pair2 < quantity_pair3:
                    quantity_pair3 = quantity_pair2
                else:
                    quantity_pair2 = quantity_pair3
                balance_currency2 = (balance_currency3 - balance_currency3 * settings.fee) * price_pair2

                if quantity_pair1 < balance_currency2:
                    balance_currency2 = quantity_pair1
                    quantity_pair2 = balance_currency2
                    balance_currency3 = balance_currency2 / price_pair2
                    balance_currency3 += balance_currency3 * settings.fee
                    quantity_pair3 = balance_currency3
                else:
                    quantity_pair1 = balance_currency2

                if not check_min_size(market_raw, triangular, [quantity_pair1, quantity_pair2, quantity_pair3]):
                    print('Size too small')
                    continue
                if price_pair3 * quantity_pair3 < 0.0011:
                    print('Min trade requirement not meet (< 0.0011)')
                    continue

                print('buy {0}-{1}, price {2}, quantity {3}'.format(currency1, currency3, price_pair3, quantity_pair3))
                rs = bittrex_api.buylimit('{0}-{1}'.format(currency1, currency3), quantity_pair3, price_pair3)
                print(rs)

                balances = bittrex_api.getbalances()
                quantity_pair2 = find_balance(balances, currency3)
                print('sell {0}-{1}, price {2}, quantity {3}'.format(currency2, currency3, price_pair2, quantity_pair2))
                rs = bittrex_api.selllimit('{0}-{1}'.format(currency2, currency3), quantity_pair2, price_pair2)
                print(rs)

                balances = bittrex_api.getbalances()
                quantity_pair1 = find_balance(balances, currency2)
                print('sell {0}-{1}, price {2}, quantity {3}'.format(currency1, currency2, price_pair1, quantity_pair1))
                rs = bittrex_api.selllimit('{0}-{1}'.format(currency1, currency2), quantity_pair1, price_pair1)
                print(rs)

        sys.stdout.write('.')
        sys.stdout.flush()


if __name__ == "__main__":
    main_loop()


