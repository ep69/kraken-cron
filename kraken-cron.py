#!/usr/bin/env python3

# Buy coins on kraken.com

import sys
import argparse
import logging
import requests
import json
import krakenex

logging.basicConfig()
log = logging.getLogger("kraken-cron")
log.setLevel(logging.INFO)

dryrun = False

k = krakenex.API()

CK = {
    "eur": "ZEUR",
    "usd": "ZUSD",
    "btc": "XXBT",
    "ltc": "XLTC",
    "xmr": "XXMR",
    "bch": "BCH",
}


def CURRENCY(c):
    return CK.get(c.lower(), None)


# https://support.kraken.com/hc/en-us/articles/205893708-Minimum-order-size-volume-for-trading
M = {  # minimum amounts to buy
    "XXBTZEUR": 0.001,
    "XXMRZEUR": 0.1,
    "XLTCZEUR": 0.1,
}


def MIN(buy, sell):
    pair = f"{CURRENCY(buy)}{CURRENCY(sell)}"
    return M.get(pair, None)


def get_price(buy, sell):
    log.debug(f"Getting price {buy}-{sell}")
    pair = f"{CURRENCY(buy)}{CURRENCY(sell)}"
    url = f"https://api.kraken.com/0/public/Ticker?pair={pair}"
    response = requests.get(url)
    data = json.loads(response.text)
    log.debug(f"Retuned data: {data}")
    return float(data["result"][pair]["c"][0])


def get_balance(currency):
    log.debug("Getting balance")
    data = k.query_private('Balance')
    log.debug(f"Retuned: {data}")
    # kraken currency symbol
    kcs = CURRENCY(currency)
    bal = float(data["result"].get(kcs, 0))
    log.debug(f"Balance {bal} {currency} ({kcs})")
    return bal


def buy(buy_currency, amount, sell_currency):
    log.debug(f"Buying {amount} {buy_currency}")
    pair = f"{CURRENCY(buy_currency)}{CURRENCY(sell_currency)}"
    data = {
        'pair': pair,
        'type': 'buy',
        'ordertype': 'market',
        'leverage': 'none',
        'volume': str(amount),
    }
    if dryrun:
        log.debug("Dryrun, just validate the transaction")
        data['validate'] = True
    log.debug(f"Request: AddOrder {data}")
    reply = k.query_private('AddOrder', data)
    log.debug(f"Retuned: {reply}")


def main():
    ap = argparse.ArgumentParser(description="Buy coins through Kraken API")
    ap.add_argument("-k", "--key", default=f"{sys.path[0]}/api.key",
                    help="API key filename "
                         "(default: api.key in script directory)")
    ap.add_argument("-d", "--dry-run", action="store_true",
                    help="dry run - do not buy anything")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="verbose - print debug messages")
    ap.add_argument("-a", "--amount", type=float, default=0.0,
                    help="amount to spend (default: minimum)")
    ap.add_argument("-b", "--buy", default="BTC",
                    help="currency to buy (default: BTC)")
    ap.add_argument("-s", "--sell", default="EUR",
                    help="currency to sell (default: EUR)")
    args = ap.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)
    log.debug(f"Args: {args}")

    global dryrun
    dryrun = args.dry_run

    log.debug(f"Key: {args.key}")
    # load key
    k.load_key(args.key)

    buy_currency = args.buy
    if not CURRENCY(buy_currency):
        log.error(f"Unknown currency to buy: '{buy_currency}'")
    sell_currency = args.sell
    if not CURRENCY(sell_currency):
        log.error(f"Unknown currency to sell: '{sell_currency}'")

    price = get_price(buy_currency, sell_currency)
    eur = get_balance(sell_currency)

    if args.amount == 0.0:
        log.debug("Default amount")
        minimum = MIN(buy_currency, sell_currency)
        if not minimum:
            log.error(f"Unknown minimum for {buy_currency}-{sell_currency}, "
                      f"specify amount explicitly")
            sys.exit(1)
        amount = minimum
        cost = amount * price
    else:
        log.debug(f"Specific amount - {args.amount}")
        amount = args.amount / price
        cost = args.amount
    log.info(f"Buy {amount} {buy_currency} for {cost} {sell_currency}; "
             f"price {price} {sell_currency}/{buy_currency}; "
             f"balance {eur} {sell_currency}")

    if 1.1 * cost > eur:
        log.error(f"Error - no enough {sell_currency} (keeping 10% buffer)")
        return 1

    buy(buy_currency, amount, sell_currency)

    return 0


if __name__ == "__main__":
    sys.exit(main())
