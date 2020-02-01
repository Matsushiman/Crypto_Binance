#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import ccxt
from time import sleep
from credentials import API_KEY, SECRET_KEY

base = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(base + '/python')

BASE_CURRENCY = "USDT"
REQUIRED_CURRENCY = "BTC"

LOWEST_RATE = 999999.0
HIGHEST_RATE = 0.0
PROFIT_BOARDER = 0.0
RETRY_COUNT = 30
WAIT_IN_SEC = 3.0

FEE_RATE_STANDARD = 0.001
FEE_RATE_BNB = 0.0005
ORDER_AMOUNT_IN_STD = 15.0


def print_exchanges():
    print('Supported exchanges:', ', '.join(ccxt.exchanges))


def print_usage():
    print("Usage: python", sys.argv[0], 'id')
    print("python", sys.argv[0], 'kraken')
    print("python", sys.argv[0], 'gdax')
    print_exchanges()


def exclude_fee(cost, symbol):
    if symbol.startswith('BNB') or symbol.endswith('BNB'):
        return cost/(1.0 + FEE_RATE_BNB)
    else:
        return cost/(1.0 + FEE_RATE_STANDARD)


def get_profit(exchange, target_currencies):

    conversion_rate = 0.00000001

    try:
        tickers = exchange.fetch_tickers()
        normal_rate_ask = tickers[f'{REQUIRED_CURRENCY}/{BASE_CURRENCY}']['ask']
        normal_rate_bid = tickers[f'{REQUIRED_CURRENCY}/{BASE_CURRENCY}']['bid']

        for c in target_currencies:
            rate_required_bid = tickers[f'{c}/{REQUIRED_CURRENCY}']['bid']
            rate_base_ask = tickers[f'{c}/{BASE_CURRENCY}']['ask']

            if rate_required_bid > 0 and rate_base_ask > 0:
                rate_candidate = rate_required_bid*normal_rate_bid/rate_base_ask

                if rate_candidate > conversion_rate:
                    target_currency = c
                    target_first = True
                    conversion_rate = rate_candidate

        print(
            '{0}/{1} Ask {2:.8f} '.format(
                target_currency, BASE_CURRENCY,
                tickers[f'{target_currency}/{BASE_CURRENCY}']['ask']),
            '{0}/{1} Bid {2:.8f} '.format(
                target_currency, REQUIRED_CURRENCY,
                tickers[f'{target_currency}/{REQUIRED_CURRENCY}']['bid']),
            '{0}/{1} Bid {2:.8f} '.format(
                REQUIRED_CURRENCY, BASE_CURRENCY,
                normal_rate_bid),
            'Conv {0:.8f}'.format(conversion_rate)
        )

        for c in target_currencies:
            rate_required_ask = tickers[f'{c}/{REQUIRED_CURRENCY}']['ask']
            rate_base_bid = tickers[f'{c}/{BASE_CURRENCY}']['bid']

            if rate_required_ask > 0 and rate_base_bid > 0:
                rate_candidate = rate_base_bid / \
                    (normal_rate_ask*rate_required_ask)

                if rate_candidate > conversion_rate:
                    target_currency = c
                    target_first = False
                    conversion_rate = rate_candidate

        print(
            '{0}/{1} Ask {2:.8f} '.format(
                REQUIRED_CURRENCY, BASE_CURRENCY,
                normal_rate_ask),
            '{0}/{1} Ask {2:.8f} '.format(
                target_currency, REQUIRED_CURRENCY,
                tickers[f'{target_currency}/{REQUIRED_CURRENCY}']['ask']),
            '{0}/{1} Bid {2:.8f} '.format(
                target_currency, BASE_CURRENCY,
                tickers[f'{target_currency}/{BASE_CURRENCY}']['bid']),
            'Conv {0:.8f}'.format(conversion_rate)
        )

        profit_set = {
            'ask_rate': normal_rate_ask,
            'bid_rate': normal_rate_bid,
            'target_currency': target_currency,
            'target_first': target_first,
            'conversion_rate': conversion_rate,
            'profit': conversion_rate/(1.001*1.0005**2) -
            1 if BASE_CURRENCY == 'BNB' or REQUIRED_CURRENCY == 'BNB' else conversion_rate/(1.001**3) - 1
        }
        print('Highest Profit by Conversion Rate: {0:.8f} {1}/{2}, To buy {3} {4}'.format(
            conversion_rate /
            (1.001*1.0005**2) -
            1 if BASE_CURRENCY == 'BNB' or REQUIRED_CURRENCY == 'BNB' else conversion_rate/(1.001**3) - 1,
            REQUIRED_CURRENCY, BASE_CURRENCY, target_currency, 'first' if target_first else 'seccond'))
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


def post_order_chain(exchange, profit_info, test_mode):

    if profit_info['target_first']:
        # Base CurrencyをTarget Currencyに換算
        # X = ORDER_AMOUNT_IN_STD/rate_base_ask*(1+手数料率) TARGET
        symbol = f'{profit_info["target_currency"]}/{BASE_CURRENCY}'
        ticker = exchange.fetch_ticker(symbol)
        amount = ORDER_AMOUNT_IN_STD/ticker['ask']
        # Target Currencyを購入
        order_result = post_order(
            exchange, symbol, 'buy', exclude_fee(amount, symbol), test_mode)
        # 購入数量を取得
        amount = order_result['filled'] if not test_mode else exclude_fee(
            amount, symbol)
        # Target Currencyを売却
        symbol = f'{profit_info["target_currency"]}/{REQUIRED_CURRENCY}'
        ticker = exchange.fetch_ticker(symbol)
        order_result = post_order(
            exchange, symbol, 'sell', exclude_fee(amount, symbol), test_mode)
        # 売却数量を取得
        amount = order_result['filled'] if not test_mode else exclude_fee(
            amount, symbol)
        # Target CurrencyをRequired Currencyに換算
        # Y = X*rate_required_bid/(1+手数料率) REQUIRED
        amount = amount*ticker['bid']
        print('Bought Amount: {0:.8f} ({1})'.format(amount, REQUIRED_CURRENCY))

        # Required Currencyを売却
        symbol = f'{REQUIRED_CURRENCY}/{BASE_CURRENCY}'
        ticker = exchange.fetch_ticker(symbol)
        order_result = post_order(
            exchange, symbol, 'sell', exclude_fee(amount, symbol), test_mode)
        # 売却数量を取得
        amount = order_result['filled'] if not test_mode else exclude_fee(
            amount, symbol)
        # Required CurrencyをBase Currencyに換算
        # Z = Y*normal_rate_bid/(1+手数料率) BASE
        amount = amount*ticker['bid']
        print('Sold Amount: {0:.8f} ({1})'.format(amount, BASE_CURRENCY))
    else:
        # Base CurrencyをRequired Currencyに換算
        # X = ORDER_AMOUNT_IN_STD/normal_rate_ask*(1+手数料率) REQUIRED
        symbol = f'{REQUIRED_CURRENCY}/{BASE_CURRENCY}'
        ticker = exchange.fetch_ticker(symbol)
        amount = ORDER_AMOUNT_IN_STD/ticker['ask']
        # Required Currencyを購入
        order_result = post_order(
            exchange, symbol, 'buy', exclude_fee(amount, symbol), test_mode)
        # 購入数量を取得
        amount = order_result['filled'] if not test_mode else exclude_fee(
            amount, symbol)
        # Required CurrencyをTarget Currencyに換算
        # Y = X/rate_required_ask*(1+手数料率) TARGET
        symbol = f'{profit_info["target_currency"]}/{REQUIRED_CURRENCY}'
        ticker = exchange.fetch_ticker(symbol)
        amount = amount/ticker['bid']
        # Target Currencyを購入
        order_result = post_order(
            exchange, symbol, 'buy', exclude_fee(amount, symbol), test_mode)
        # 購入数量を取得
        amount = order_result['filled'] if not test_mode else exclude_fee(
            amount, symbol)
        print('Bought Amount: {0:.8f} ({1})'.format(
            amount, profit_info["target_currency"]))

        # Target Currencyを売却
        symbol = f'{profit_info["target_currency"]}/{BASE_CURRENCY}'
        ticker = exchange.fetch_ticker(symbol)
        order_result = post_order(
            exchange, symbol, 'sell', exclude_fee(amount, symbol), test_mode)
        # 売却数量を取得
        amount = order_result['filled'] if not test_mode else exclude_fee(
            amount, symbol)
        # Target CurrencyをBase Currencyに換算
        # Z = Y*normal_rate_bid/(1+手数料率) BASE
        amount = amount*ticker['bid']
        print('Sold Amount: {0:.8f} ({1})'.format(amount, BASE_CURRENCY))

    profit_in_base = amount - ORDER_AMOUNT_IN_STD
    print('Profit Amount: {0:.8f} ({1}) = {2:.8f} (JPY)'.format(
        profit_in_base, BASE_CURRENCY, profit_in_base*110))


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
    symbols_required = [m["symbol"]
                        for m in all_markets if m["symbol"].endswith(REQUIRED_CURRENCY)]
    print(f'Num of Symbols with Required Currency: {len(symbols_required)}')
    symbols_base = [m["symbol"]
                    for m in all_markets if m["symbol"].endswith(BASE_CURRENCY)]
    print(f'Num of Symbols with Base Currency: {len(symbols_base)}')

    target_currencies = []
    for s_required in symbols_required:
        if s_required.replace(REQUIRED_CURRENCY, BASE_CURRENCY) in symbols_base:
            target_currencies.append(
                s_required.replace(f'/{REQUIRED_CURRENCY}', ""))

    print(f'Num of Target Currencies: {len(target_currencies)}')
###########

    for i in range(RETRY_COUNT):
        profit_info = get_profit(exchange, target_currencies)
        profit = profit_info['profit']
        if profit > PROFIT_BOARDER:
            break
        sleep(WAIT_IN_SEC)
    else:
        print("Profit Check timeout.")
        sys.exit(2)

    test_mode = len(sys.argv) > 1 and sys.argv[1] == 'test'

    post_order_chain(exchange, profit_info, test_mode)

except Exception as e:

    print(type(e).__name__, e.args, str(e))
    print_usage()
