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
log = logging.getLogger("kc-withdraw")
log.setLevel(logging.INFO)

dryrun = False

k = krakenex.API()

CK = {
    "btc": "XXBT",
    "ltc": "XLTC",
    "xmr": "XXMR",
    "eth": "XETH",
}


def CURRENCY(c):
    return CK.get(c.lower(), None)


# https://support.kraken.com/hc/en-us/articles/360000767986-Cryptocurrency-withdrawal-fees-and-minimums
MIN_WITHDRAW = {  # minimum amounts to withdraw
    "XXBT": 0.0005
}


def min_withdraw(cur):
    m = MIN_WITHDRAW.get(CURRENCY(cur), None)
    if m is None:
        log.warn(f"Unknown Kraken minimum for {cur}, assuming 0.0")
        m = 0.0
    return m


def get_balance(currency):
    log.debug("Getting balance")
    data = k.query_private('Balance')
    log.debug(f"Retuned: {data}")
    # kraken currency symbol
    kcs = CURRENCY(currency)
    bal = float(data["result"].get(kcs, 0))
    log.debug(f"Balance {bal} {currency} ({kcs})")
    return bal


def withdraw(currency, amount, wallet):
    log.debug(f"Withdrawing {amount} {currency}")
    data = {
        'nonce': str(int(1000*time.time())),
        'asset': CURRENCY(currency),
        'key': wallet,
        'amount': str(amount),
    }

    log.debug(f"Request: Withdraw {data}")

    if dryrun:
        log.debug("Dryrun, just validate the transaction")
        #data['validate'] = True # this does NOT work for Withdraw
        return ["Validation only"]

    reply = k.query_private('Withdraw', data)
    log.debug(f"Retuned: {reply}")

    return reply['error']


def main():
    ap = argparse.ArgumentParser(description="Buy coins through Kraken API")
    ap.add_argument("-k", "--key", help="API key filename, REQUIRED")
    ap.add_argument("-d", "--dry-run", action="store_true",
                    help="dry run - do not buy anything")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="verbose - print debug messages")
    ap.add_argument("-a", "--amount", default="all",
                    help="amount to withdraw (default: all)")
    ap.add_argument("-m", "--min", type=float, default=0.0,
                    help="minimal amount to withdraw (default: 0.0)")
    ap.add_argument("-c", "--currency", default="BTC",
                    help="currency to withdraw (default: BTC)")
    ap.add_argument("-w", "--wallet",
                    help="wallet name, REQUIRED")
    args = ap.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)
    log.debug(f"Args: {args}")

    global dryrun
    dryrun = args.dry_run

    log.debug(f"Key: {args.key}")
    if not args.key:
        log.error(f"No key specified")
        return 1
    # load key
    k.load_key(args.key)

    currency = args.currency
    if not CURRENCY(currency):
        log.error(f"Unknown currency to withdraw: '{currency}'")
        return 1

    wallet = args.wallet
    if not wallet:
        log.error(f"No wallet specified")
        return 1

    amount = 0.0 if args.amount == "all" else float(args.amount)
    minimum = args.min
    balance = "unknown"
    min_s = ""
    if minimum or not amount:
        balance = get_balance(currency)
        if not amount:
            log.debug(f"Withdrawing all {currency}")
            amount = balance
        if minimum:
            min_s = f" if {balance} >= {minimum}"
    log.info(f"Planning to withdraw {amount} {currency}{min_s}")
    if amount < minimum:
        log.info(f"Not withdrawing, {amount} < {minimum} "
                 "(user provided minimum)")
        return 0

    min_kraken = min_withdraw(currency)
    if amount < min_kraken:
        log.error(f"Amount to withdraw {amount} < {min_kraken} {currency} "
                  "(Kraken minimum)")
        return 1

    error = withdraw(currency, amount, wallet)
    if error:
        for m in error:
            log.error(f"Withdraw error: {m}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
