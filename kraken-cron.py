#!/usr/bin/env python3

# Buy coins on kraken.com

import sys
import argparse
import logging
import requests
import json
import time
import krakenex

logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s %(message)s')
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
    "eth": "XETH",
}


def CURRENCY(c):
    return CK.get(c.lower(), None)


# https://support.kraken.com/hc/en-us/articles/205893708-Minimum-order-size-volume-for-trading
M = {  # minimum amounts to buy
    "XXBTZEUR": 0.0002,
    "XXMRZEUR": 0.05,
    "XLTCZEUR": 0.05,
    "BCHEUR": 0.02,
    "XETHZEUR": 0.005,
}


def PAIR(buy, sell):
    b = CURRENCY(buy)
    s = CURRENCY(sell)
    assert(len(b) >= 3)
    assert(len(b) <= 4)
    assert(len(s) >= 3)
    assert(len(s) <= 4)
    if len(b) == 3 or len(s) == 3:
        b = b[-3:]
        s = s[-3:]
    return f"{b}{s}"


def MIN(buy, sell):
    pair = PAIR(buy, sell)
    return M.get(pair, None)


def get_price(buy, sell):
    log.debug(f"Getting price {buy}-{sell}")
    pair = PAIR(buy, sell)
    url = f"https://api.kraken.com/0/public/Ticker?pair={pair}"
    response = requests.get(url)
    data = json.loads(response.text)
    log.debug(f"Returned data: {data}")
    result = data.get("result", None)
    if result is None:
        return None
    return float(result[pair]["c"][0])


def get_balance(currency):
    log.debug("Getting balance")
    data = k.query_private('Balance')
    log.debug(f"Returned: {data}")
    result = data.get("result", None)
    if result is None:
        return None
    # kraken currency symbol
    kcs = CURRENCY(currency)
    bal = float(result.get(kcs, 0))
    log.debug(f"Balance {bal} {currency} ({kcs})")
    return bal


def buy(buy_currency, amount, sell_currency):
    log.debug(f"Buying {amount} {buy_currency}")
    pair = PAIR(buy_currency, sell_currency)
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
    log.debug(f"Returned: {reply}")

    return reply['error']


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
    ap.add_argument("-t", "--amount-type", default="sell",
                    help="amount type - buy / sell (default: sell)")
    ap.add_argument("-b", "--buy", default="BTC",
                    help="currency to buy (default: BTC)")
    ap.add_argument("-s", "--sell", default="EUR",
                    help="currency to sell (default: EUR)")
    ap.add_argument("-c", "--check-balance", action="store_true",
                    help="check balance before issuing order")
    args = ap.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)
    log.debug(f"Args: {args}")

    global dryrun
    dryrun = args.dry_run

    checkbal = args.check_balance
    log.debug(f"Check balance: {checkbal}")

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

    sell_balance = "unknown"
    if checkbal:
        sell_balance = get_balance(sell_currency)

    amount_type = args.amount_type
    if amount_type not in ["sell", "buy"]:
        log.error(f"Amount type error: {amount_type}")
        sys.exit(1)
    if args.amount == 0.0:
        log.debug("Default amount")
        minimum = MIN(buy_currency, sell_currency)
        if not minimum:
            log.error(f"Unknown minimum for {buy_currency}-{sell_currency}, "
                      f"specify amount explicitly")
            sys.exit(1)
        buy_amount = minimum
        sell_amount = buy_amount * price
    else:
        if amount_type == "sell":
            log.debug(f"Specific amount to spend: "
                      f"{args.amount} {sell_currency}")
            buy_amount = args.amount / price
            sell_amount = args.amount
        elif amount_type == "buy":
            log.debug(f"Specific amount to buy: "
                      f"{args.amount} {buy_currency}")
            buy_amount = args.amount
            sell_amount = args.amount * price
        else:
            assert(False)

    log.info(f"Buy {buy_amount} {buy_currency} "
             f"for {sell_amount} {sell_currency}; "
             f"price {price} {sell_currency}/{buy_currency}; "
             f"balance {sell_balance} {sell_currency}")

    minimum = MIN(buy_currency, sell_currency)
    if minimum and buy_amount < minimum:
        log.error(f"Planning to buy {buy_amount} {buy_currency} "
                  f"for {sell_amount} {sell_currency}, "
                  f"MINIMUM is {minimum} {buy_currency}")
        sys.exit(1)

    if checkbal:
        if 1.1 * sell_amount > sell_balance:
            log.error(f"Error - not enough {sell_currency} (keeping 10% buffer)")
            return 1

    t = 0
    MAX_TRIES = 5
    DELAY = 30
    while t < MAX_TRIES:
        log.debug(f"Buy loop: iteration {t}")
        t += 1
        error = buy(buy_currency, buy_amount, sell_currency)
        recoverable_errors = ("EService:Busy", "EGeneral:Internal error")
        if len(error) >= 1 and error[0] in recoverable_errors:
            log.debug(f"Buy loop: recoverable problem, waiting {DELAY} seconds")
            time.sleep(DELAY)
        elif error:
            log.debug(f"Buy loop: other error {error}")
            for m in error:
                log.error(f"Buy error: {m}")
            sys.exit(1)
        else: # success
            log.debug(f"Buy loop: success")
            break

    return 0


if __name__ == "__main__":
    sys.exit(main())
