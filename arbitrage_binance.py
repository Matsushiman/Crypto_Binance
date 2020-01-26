# -*- coding: utf-8 -*-

import os
import sys
import ccxt
from time import sleep
from credentials import API_KEY, SECRET_KEY

root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root + '/python')

STANDARD_CURRENCY = "USDT"
WISHING_CURRENCY = "BTC"

LOWEST_RATE = 999999.0
HIGHEST_RATE = 0.0
PROFIT_BOARDER = 7.0
RETRY_COUNT = 30
WAIT_IN_SEC = 3.0

ORDER_FEE_RATE = 0.001
ORDER_AMOUNT_IN_STD = 15.0


def print_exchanges():
    print('Supported exchanges:', ', '.join(ccxt.exchanges))


def print_usage():
    print("Usage: python", sys.argv[0], 'id')
    print("python", sys.argv[0], 'kraken')
    print("python", sys.argv[0], 'gdax')
    print_exchanges()


def exclude_fee(cost):
    return cost/(1.0 + ORDER_FEE_RATE)


def get_profit(exchange):

    lowest_rate = LOWEST_RATE
    highest_rate = HIGHEST_RATE

    try:
        tickers = exchange.fetch_tickers()
        ticker_ask = tickers[f'{WISHING_CURRENCY}/{STANDARD_CURRENCY}']['ask']
        ticker_bid = tickers[f'{WISHING_CURRENCY}/{STANDARD_CURRENCY}']['bid']
        for c in target_currencies:
            ticker_wishing_ask = tickers[f'{c}/{WISHING_CURRENCY}']['ask']
            ticker_wishing_bid = tickers[f'{c}/{WISHING_CURRENCY}']['bid']
            ticker_std_ask = tickers[f'{c}/{STANDARD_CURRENCY}']['ask']
            ticker_std_bid = tickers[f'{c}/{STANDARD_CURRENCY}']['bid']

            if ticker_wishing_ask > 0 and ticker_wishing_bid > 0 and ticker_std_ask > 0 and ticker_std_bid > 0:
                rate_buy = ticker_std_ask/ticker_wishing_bid
                rate_sell = ticker_std_bid/ticker_wishing_ask
                # print(
                #     c,
                #     'Ask {0:.8f}'.format(
                #         ticker_std_ask) + f'({c}/{STANDARD_CURRENCY}),',
                #     'Bid {0:.8f}'.format(
                #         ticker_wishing_bid) + f'({c}/{WISHING_CURRENCY}),',
                #     'Rate {0:.8f}'.format(
                #         rate_buy) + f'({STANDARD_CURRENCY}/{WISHING_CURRENCY})',
                #     'Ask {0:.8f}'.format(
                #         ticker_wishing_ask) + f'({c}/{WISHING_CURRENCY}),',
                #     'Bid {0:.8f}'.format(
                #         ticker_std_bid) + f'({c}/{STANDARD_CURRENCY}),',
                #     'Rate {0:.8f}'.format(
                #         rate_sell) + f'({STANDARD_CURRENCY}/{WISHING_CURRENCY})'
                # )

                if rate_buy < lowest_rate:
                    lowest_currency = c
                    lowest_rate = rate_buy
                if rate_sell > highest_rate:
                    highest_currency = c
                    highest_rate = rate_sell

        print(
            f'Stardard Market:',
            '\t',
            'Ask {0:.8f}'.format(
                ticker_ask),
            f'{WISHING_CURRENCY}/{STANDARD_CURRENCY}',
            '\t',
            'Bid {0:.8f}'.format(
                ticker_bid),
            f'{WISHING_CURRENCY}/{STANDARD_CURRENCY}'
        )
        print(
            f'Lowest Market: {lowest_currency}',
            '\t',
            'Ask {0:.8f}'.format(
                tickers[f'{lowest_currency}/{STANDARD_CURRENCY}']['ask']),
            f'{lowest_currency}/{STANDARD_CURRENCY}',
            '\t',
            'Bid {0:.8f}'.format(
                tickers[f'{lowest_currency}/{WISHING_CURRENCY}']['bid']),
            f'{lowest_currency}/{WISHING_CURRENCY}',
            '\t',
            '{0:.8f}'.format(lowest_rate) +
            f' {WISHING_CURRENCY}/{STANDARD_CURRENCY}(Conv)'
        )
        print(
            f'Highest Market: {highest_currency}',
            '\t',
            'Ask {0:.8f}'.format(
                tickers[f'{highest_currency}/{WISHING_CURRENCY}']['ask']),
            f'{highest_currency}/{WISHING_CURRENCY}',
            '\t',
            'Bid {0:.8f}'.format(
                tickers[f'{highest_currency}/{STANDARD_CURRENCY}']['bid']),
            f'{highest_currency}/{STANDARD_CURRENCY}',
            '\t',
            '{0:.8f}'.format(highest_rate) +
            f' {WISHING_CURRENCY}/{STANDARD_CURRENCY}(Conv)'
        )

        profit_set = {
            'ask_rate': ticker_ask,
            'bid_rate': ticker_bid,
            'lowest_currency': lowest_currency,
            'lowest_rate': lowest_rate,
            'highest_currency': highest_currency,
            'highest_rate': highest_rate,
            'profit': highest_rate - lowest_rate
        }
        # print('Conversion Rate Difference: {0:.8f}'.format(
        #     profit_set['profit']), f' {WISHING_CURRENCY}/{STANDARD_CURRENCY}')
        print('Lowest Conversion Rate Difference: {0:.8f}'.format(
            ticker_bid - lowest_rate), f' {WISHING_CURRENCY}/{STANDARD_CURRENCY}')
        print('Highest Conversion Rate Difference: {0:.8f}'.format(
            highest_rate - ticker_ask), f' {WISHING_CURRENCY}/{STANDARD_CURRENCY}')
        return profit_set

    except ccxt.DDoSProtection as e:
        print(type(e).__name__, e.args, 'DDoS Protection (ignoring)')
    except ccxt.RequestTimeout as e:
        print(type(e).__name__, e.args, 'Request Timeout (ignoring)')
    except ccxt.ExchangeNotAvailable as e:
        print(type(e).__name__, e.args,
              'Exchange Not Available due to downtime or maintenance (ignoring)')
    except ccxt.AuthenticationError as e:
        print(type(e).__name__, e.args,
              'Authentication Error (missing API keys, ignoring)')


def post_order(exchange, symbol, side, amount, test_mode):
    print('Order - symbol: {0}, side: {1}, amount: {2:.8f} {3}'.format(
        symbol, side, amount, symbol.split("/")[0]))
    order = exchange.create_market_order(symbol, side, amount, None, {
                                         'test': True} if test_mode else {})
    # print(order)
    return order


try:
    exchange = ccxt.binance({
        'apiKey': API_KEY,
        'secret': SECRET_KEY,
        # https://github.com/ccxt/ccxt/wiki/Manual#rate-limit
        'enableRateLimit': True
    })

    if not exchange.has['fetchTickers']:
        msg = 'Exchange ' + exchange.id + \
            ' does not have the endpoint to fetch all tickers from the API.'
        raise ccxt.NotSupported(msg)

    # load all markets from the exchange
    markets = exchange.load_markets()

###########

    all_markets = exchange.fetch_markets()
    symbols_wishing = [m["symbol"]
                       for m in all_markets if m["id"].endswith(WISHING_CURRENCY)]
    symbols_std = [m["symbol"]
                   for m in all_markets if m["id"].endswith(STANDARD_CURRENCY)]

    target_currencies = []
    for s_wishing in symbols_wishing:
        if s_wishing.replace(WISHING_CURRENCY, STANDARD_CURRENCY) in symbols_std:
            target_currencies.append(
                s_wishing.replace(f'/{WISHING_CURRENCY}', ""))

    print(f'Num of Target Currencies: {len(target_currencies)}')
###########

    for i in range(RETRY_COUNT):
        result = get_profit(exchange)
        diff_lowest = result['bid_rate'] - result['lowest_rate']
        # diff_highest = result['highest_rate'] - result['ask_rate']
        # if diff_lowest > PROFIT_BOARDER and diff_highest > PROFIT_BOARDER:
        if diff_lowest > PROFIT_BOARDER:
            break
        sleep(WAIT_IN_SEC)
    else:
        print("Profit Check timeout.")
        sys.exit(2)

    test_mode = len(sys.argv) > 1 and sys.argv[1] == 'test'

    symbol = f'{result["lowest_currency"]}/{STANDARD_CURRENCY}'
    ticker = exchange.fetch_ticker(symbol)
    amount = ORDER_AMOUNT_IN_STD/ticker['ask']
    order_result = post_order(exchange, symbol, 'buy',
                              exclude_fee(amount), test_mode)
    amount = order_result['filled'] if not test_mode else amount

    symbol = f'{result["lowest_currency"]}/{WISHING_CURRENCY}'
    ticker = exchange.fetch_ticker(symbol)
    order_result = post_order(exchange, symbol, 'sell',
                              exclude_fee(amount), test_mode)
    amount = order_result['filled'] if not test_mode else amount
    amount = amount*ticker['bid']
    print('Bought Amount: {0:.8f} ({1})'.format(amount, WISHING_CURRENCY))

    lowest_rate = result['lowest_rate']
    for i in range(RETRY_COUNT):
        result = get_profit(exchange)
        if exclude_fee(exclude_fee(amount))*result['highest_rate'] - ORDER_AMOUNT_IN_STD > 0:
            symbol = f'{result["highest_currency"]}/{WISHING_CURRENCY}'
            ticker = exchange.fetch_ticker(symbol)
            amount = amount/ticker['ask']
            order_result = post_order(
                exchange, symbol, 'buy', exclude_fee(amount), test_mode)
            amount = order_result['filled'] if not test_mode else amount

            symbol = f'{result["highest_currency"]}/{STANDARD_CURRENCY}'

            break
        sleep(WAIT_IN_SEC)
    else:
        symbol = f'{WISHING_CURRENCY}/{STANDARD_CURRENCY}'

    ticker = exchange.fetch_ticker(symbol)
    order_result = post_order(exchange, symbol, 'sell',
                              exclude_fee(amount), test_mode)
    amount = order_result['filled'] if not test_mode else amount
    amount = amount*ticker['bid']
    print('Sold Amount: {0:.8f} ({1})'.format(amount, STANDARD_CURRENCY))

    profit_in_std = amount - ORDER_AMOUNT_IN_STD
    print('Profit Amount: {0:.8f} ({1}) = {2:.8f} (JPY)'.format(
        profit_in_std, STANDARD_CURRENCY, profit_in_std*110))


except Exception as e:

    print(type(e).__name__, e.args, str(e))
    print_usage()
