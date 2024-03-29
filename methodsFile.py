import alpaca_trade_api as tradeapi
import time
import threading
import math

class order_stuff:
    '''
    This class has functions that are used to do different types of orders
    None of these return anything and are used to execure orders
    '''
    def __init__(self):
        API_KEY = [API KEY]
        API_SECRET = [API KEY]
        APCA_API_BASE_URL = 'https://paper-api.alpaca.markets'
        self.alpaca = tradeapi.REST(API_KEY, API_SECRET, APCA_API_BASE_URL, 'v2')

        self.long = []
        self.short = []
        self.qShort = None
        self.qLong = None
        self.adjustedQLong = None
        self.adjustedQShort = None
        self.blacklist = set()
        self.longAmount = 0
        self.shortAmount = 0
        self.timeToClose = None

    # Make a method to close all positions
    def close_all_positions(self, runcount, cursor):
    '''
    This class is used to close all positition. Does not return anything.
    '''    
        base_endpoint = 'https://paper-api.alpaca.markets'
        api_key_id = [API KEY]
        secret_key = [API KEY]
        api = tradeapi.REST(api_key_id, secret_key, base_url=base_endpoint)

        positions = api.list_positions()
        for position in positions:
            if (position.side == 'long'):
                orderSide = 'sell'
            else:
                orderSide = 'buy'
            qty = abs(int(float(position.qty)))
            respSO = []
            try:
                tSubmitOrder = threading.Thread(
                    target=api.submit_order(position.symbol, int(float(qty)), orderSide, 'market', 'day'))
                tSubmitOrder.start()
                tSubmitOrder.join()
                # Add to database
                cursor.execute(
                    "INSERT INTO orders VALUES (" + str(runcount) + ",'" + position.symbol + "'," + str(
                        time) + "," + str(
                        int(float(qty))) + "," + str(position.market_value) + ",'" + orderSide + "')")
            except:
                print("There was a problem closing the positions")

    def buying(self, targetTicker, portfolio_ticker_list, runcount, cursor):
        '''
        This class is used to buy a single stock out of a list of interesting tickers
        '''
        if targetTicker not in portfolio_ticker_list:
            base_endpoint = 'https://paper-api.alpaca.markets'
            api_key_id = [API KEY]
            secret_key = [API KEY]

            api = tradeapi.REST(api_key_id, secret_key, base_url=base_endpoint)

            last_quote = api.get_last_quote(targetTicker)
            share_price = last_quote.askprice

            account = api.get_account()
            cash = account.cash
            portfolio = api.list_positions()
            number_of_equities = len(portfolio)
            # If there are no current securities, use half of our cash to buy the targetTicker
            if number_of_equities == 0 or number_of_equities == 1:
                amount_to_invest = int(float(cash)) / 2
                share_count_to_buy = amount_to_invest / float(share_price)
                try:
                    tSubmitOrder = threading.Thread(
                        target=api.submit_order(targetTicker, share_count_to_buy, 'buy', 'market', 'day'))
                    print('Buying ', share_count_to_buy, ' shares of ', targetTicker, 'at ', share_price, ' per share')
                    tSubmitOrder.start()
                    tSubmitOrder.join()
                    # Add to database
                    cursor.execute(
                        "INSERT INTO orders VALUES (" + str(runcount) + ",'" + targetTicker + "'," + str(
                            time) + "," + str(
                            int(float(
                                share_count_to_buy))) + "," + share_count_to_buy * share_price + ",'" + 'buy' + "')")
                except:
                    print("There was a problem placing the order")
            # If there is 1 current security, use the rest of our cash to buy the other item of interest
            if number_of_equities == 0:
                amount_to_invest = cash
                share_count_to_buy = amount_to_invest / float(share_price)
                try:
                    tSubmitOrder = threading.Thread(
                        target=api.submit_order(targetTicker, share_count_to_buy, 'buy', 'market', 'day'))
                    print('Buying ', share_count_to_buy, ' shares of ', targetTicker, 'at ', share_price, ' per share')
                    tSubmitOrder.start()
                    tSubmitOrder.join()
                    # Add to database
                    cursor.execute(
                        "INSERT INTO orders VALUES (" + str(runcount) + ",'" + targetTicker + "'," + str(
                            time) + "," + str(
                            int(float(
                                share_count_to_buy))) + "," + share_count_to_buy * share_price + ",'" + 'buy' + "')")
                except:
                    print("There was a problem placing the order")
            # If there is more than 1 security, split the equity evenly between them
            if number_of_equities > 1:
                tickers = []  # First generate a list of all tickers you want to hold
                for position in portfolio:
                    tickers.append(position.symbol)
                tickers.append(targetTicker)
                # Now that we have a list, we must close all positions
                positions = api.list_positions()
                for position in positions:
                    if (position.side == 'long'):
                        orderSide = 'sell'
                    else:
                        orderSide = 'buy'
                    qty = abs(int(float(position.qty)))
                    respSO = []
                    try:
                        tSubmitOrder = threading.Thread(
                            target=api.submit_order(position.symbol, int(float(qty)), orderSide, 'market', 'day'))
                        print('Submitting order for', qty, 'shares of ', position.symbol, ' to ', orderSide, '.')
                        tSubmitOrder.start()
                        tSubmitOrder.join()
                        # Add to database
                        cursor.execute(
                            "INSERT INTO orders VALUES (" + str(runcount) + ",'" + position.symbol + "'," + str(
                                time) + "," + str(
                                int(float(qty))) + "," + str(position.market_value) + ",'" + orderSide + "')")
                    except:
                        print("There was a problem placing the order")
                # Now we reopen all desired positions
                for symbols in tickers:
                    amount_to_invest = float(cash) / len(tickers)
                    share_count_to_buy = amount_to_invest / float(share_price)
                    share_count_to_buy = int(float(math.floor(share_count_to_buy)))
                    try:
                        tSubmitOrder = threading.Thread(
                            target=api.submit_order(symbols, share_count_to_buy, 'buy', 'market', 'day'))
                        print('Submitting order for', share_count_to_buy, 'shares of ', symbols, ' to buy.')
                        tSubmitOrder.start()
                        tSubmitOrder.join()
                        # Add to database
                        cursor.execute(
                            "INSERT INTO orders VALUES (" + str(runcount) + ",'" + position.symbol + "'," + str(
                                time) + "," + str(
                                int(float(qty))) + "," + str(position.market_value) + ",'" + orderSide + "')")
                    except:
                        print("There was a problem placing the order")
        else:
            print('Already invested in target security')

    def shorting(self, targetTicker, portfolio_ticker_list, runcount, cursor):
        '''
        This function shorts a stock given a list of potential stocks to short
        '''
        if targetTicker not in portfolio_ticker_list:
            symbol = targetTicker

            # First, open the API connection
            api = tradeapi.REST(
                'PKKSZY7HUXSG54X8GV2Q',
                'WdqcOFVTPoPYxzzV0q8UW76ad0rpcjfz0vEucaj5',
                'https://paper-api.alpaca.markets', api_version='v2'
            )

            # Identify how many stocks we want to short
            # First we get how many equities we have
            account = api.get_account()
            cash = account.cash
            # Calculate how much we can short using 1/4 of the remaining cash
            cash_to_short = float(cash) / 4
            # Get a price on our symbol
            symbol_bars = api.get_barset(symbol, 'minute', 1).df.iloc[0]
            symbol_price = symbol_bars[symbol]['close']

            shares_to_short = cash_to_short / symbol_price
            shares_to_short = int(float(math.floor(shares_to_short)))
            # The security we'll be shorting
            symbol = targetTicker

            # Submit a market order to open a short position of one share
            try:
                order = api.submit_order(symbol, shares_to_short, 'sell', 'market', 'day')
                print("first order submitted")
                print('Shorting ', shares_to_short, ' shares of ', symbol)
                # Add to database
                cursor.execute(
                    "INSERT INTO orders VALUES (" + str(runcount) + ",'" + symbol + "'," + str(time) + "," + str(
                        int(float(shares_to_short))) + "," + str(cash_to_short) + ",'" + 'sell' + "')")
            except:
                print("There was an error while attempting to place order...")

            # Submit a limit order to attempt to grow our short position
            # First, get an up-to-date price for our symbol
            symbol_bars = api.get_barset(symbol, 'minute', 1).df.iloc[0]
            symbol_price = symbol_bars[symbol]['close']
            # Submit an order for one share at that price
            try:
                order = api.submit_order(symbol, shares_to_short, 'sell', 'limit', 'day', symbol_price)
                print("Limit order submitted.")
                # Add to database
                cursor.execute(
                    "INSERT INTO orders VALUES (" + str(runcount) + ",'" + symbol + "'," + str(time) + "," + str(
                        int(float(shares_to_short))) + "," + symbol_price * shares_to_short + ",'" + 'sell' + "')")
            except:
                print("There was an error while attempting to place order...")

            # Wait a second for our orders to fill...
            print('Waiting...')
            time.sleep(1)

            # Check on our position
            try:
                position = api.get_position(symbol)
                if int(float(position.qty)) < 0:
                    print(f'Short position open for {symbol}')
            except:
                print("There was an error checking our position")
        else:
            print('Already invested in target security')
