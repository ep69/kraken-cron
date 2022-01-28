import sys
import argparse
import logging
#import requests
#import json
#import krakenex

import csv
from pprint import pformat
from decimal import Decimal
from collections import deque

logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s %(message)s')
log = logging.getLogger("kraken-tax")
log.setLevel(logging.INFO)

dryrun = False

def error(m):
    print(f"ERROR: {m}")
    sys.exit(1)

known_crypto = ("XLM", "XBT", "XMR", "BCH", "ETH", "NANO", "LTC", "REPV2", "EOS", "XDG", "XRP", "UNI", "USDT")
known_fiat = ("EUR", "USD")

def parse_pair(pair):
    index = 0
    for c in known_crypto:
        if pair.startswith(c):
            base = c
            index = len(c)
            break
        elif pair.startswith(f"X{c}"):
            base = c
            index = len(c) + 1
            break
    if not index:
        error(f"parse_pair: cannot parse base of {pair}")
    rest = pair[index:]
    found = False
    for c in known_crypto:
        if rest.startswith(c) or rest.startswith(f"X{c}"):
            quote = c
            found = True
            break
    if not found:
        for f in known_fiat:
            if rest.startswith(f) or rest.startswith(f"Z{f}"):
                quote = f
                found = True
                break
    if not found:
        error(f"parse_pair: cannot parse {pair}")

    return (base, quote)

def ryear(row):
    return int(row['time'][0:4])

def rstring(row):
    base, quote = parse_pair(row["pair"])
    return f"{row['time'].split()[0]} {row['type']:<4} {float(row['vol']):>11.4f} {base:<5} for {float(row['cost']):>10.4f} {quote:<5} (price {float(row['price']):>10.4f}, fee {float(row['fee']):>9.6f})"

def rprint(row):
    print(rstring(row))

def main():
    tax_year = 2021
    main_currency = "EUR"

    infile = "trades.csv"
    if infile:
        print(f"Opening {infile}")
        f = open(infile, mode="r")
    else: # use stdin
        f = sys.stdin

    
    reader = csv.DictReader(f)
    n = 0
    pairs = set()
    types = set()
    costs = set()
    data = {}
    for row in reader:
        n += 1
        if n == 1: # header
            print(f"Columns: {', '.join(row.keys())}")
        pairs |= set((row["pair"],))
        types |= set((row["type"],))
        costs |= set((row["cost"],))

        #rprint(row)

        year = ryear(row)
        if year > tax_year:
            # not looking into future
            #print(f"SKIPPING {rstring(row)}")
            continue

        pair = row["pair"]
#        if pair != "XXBTZEUR":
        if "ETH" not in pair:
#            #print(f"SKIPPING {rstring(row)}")
            continue

        if pair not in data:
            data[pair] = {
                "buy-cost": Decimal(0),
                "buy-vol": Decimal(0),
                "buy-fee": Decimal(0),
                "sell-cost": Decimal(0),
                "sell-vol": Decimal(0),
                "sell-fee": Decimal(0),
                "wa-cost": Decimal(0),
                "wa-amount": Decimal(0),
                "wa-feesum": Decimal(0),
                "wa-profits": {},
            }
        if year not in data[pair]["wa-profits"]:
            data[pair]["wa-profits"][year] = Decimal(0)

        typ = row["type"]
        cost = Decimal(row["cost"])
        vol = Decimal(row["vol"])
        fee = Decimal(row["fee"])

        data[pair][f"{typ}-cost"] += cost
        data[pair][f"{typ}-vol"] += vol
        data[pair][f"{typ}-fee"] += fee

        if typ == "sell":
            if data[pair]["wa-amount"] > Decimal(0):
                if vol > data[pair]["wa-amount"]:
                    error(f"Special case - we did not buy enough to sell")
                avg_price = data[pair]["wa-cost"] / data[pair]["wa-amount"]
                avg_fee = data[pair]["wa-feesum"] / data[pair]["wa-amount"]
                buy_cost = vol * avg_price
                # TODO is buy-fee included in cost, or extra?
                buy_fee = vol * avg_fee
                data[pair][f"wa-amount"] -= vol
                data[pair][f"wa-cost"] -= buy_cost
                data[pair][f"wa-feesum"] -= buy_fee
                #print(f"avg_price {avg_price:.2f} avg_fee {avg_fee:.2f}")
            else: # selling something not 
                buy_cost = Decimal(0)
                buy_fee = Decimal(0)
            profit = cost - buy_cost - buy_fee - fee # sell-fee
            data[pair][f"wa-profits"][year] += profit
            rprint(row)
            print(f"profit: {profit:.2f} yprofit {data[pair][f'wa-profits'][year]:.4f} buy_cost {buy_cost:.2f}")
        elif typ == "buy":
            #rprint(row)
            data[pair]["wa-feesum"] += fee
            data[pair]["wa-cost"] += cost
            data[pair]["wa-amount"] += vol
            avg_price = data[pair]["wa-cost"] / data[pair]["wa-amount"]
            amount = data[pair]["wa-amount"]
            rprint(row)
            #print(f"Average price: {avg_price:>16.4f}, amount {amount:>8.4F}")
        else:
            error(f"Unknown type: {typ}")


    if f is not sys.stdin:
        f.close()

    print()
    print("SUMMARY:")
    for pair, vals in data.items():
        print(f"{pair}:")
        print(f"  WA: cost {vals['wa-cost']:>12.4f} amount {vals['wa-amount']:>12.4f}")
        for y, p in vals["wa-profits"].items():
            print(f"    {y} profit {p:.4f} ({pair})")

    if False:
        print(f"Pairs:")
        print(f"Types:")
        print(f"Costs: {','.join(costs)}")

if __name__ == "__main__":
    sys.exit(main())
