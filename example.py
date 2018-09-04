from time import sleep
from bittrex_websocket import OrderBook
import json


def main():
    class MySocket(OrderBook):
        def on_ping(self, msg):
            pass
            # print('Received order book update for {}'.format(msg))

    # Create the socket instance
    ws = MySocket()
    # Enable logging
    ws.enable_log()
    # Define tickers
    tickers = ['BTC-ETH']
    # Subscribe to order book updates
    ws.subscribe_to_orderbook(tickers)

    while True:
        sleep(1)
        book = ws.get_order_book('BTC-ETH')
        print(json.dumps(book))
    else:
        print('Quit')
        sleep(5)


if __name__ == "__main__":
    main()