import sys
import argparse
import logging
#import requests
#import json
#import krakenex

import csv
from pprint import pformat
from decimal import Decimal

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
    year = 2021
    currency = "EUR"

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
    cumulative = {}
    for row in reader:
        n += 1
        if n == 1: # header
            print(f"Columns: {', '.join(row.keys())}")
        pairs |= set((row["pair"],))
        types |= set((row["type"],))
        costs |= set((row["cost"],))

        if ryear(row) > year:
            print(f"SKIPPING {rstring(row)}")
            continue

        pair = row["pair"]
        if pair not in cumulative:
            cumulative[pair] = {"sum": Decimal(0), "amount": Decimal(0)}

        typ = row["type"]
        if typ == "sell":
            rprint(row)
        elif typ == "buy":
            cumulative[pair]["sum"] += Decimal(row["cost"])
            cumulative[pair]["amount"] += Decimal(row["vol"])
            rprint(row)
            #print(f"Cumulative {pair}: {cumulative[pair]}")
        else:
            error(f"Unknown type: {typ}")


    if f is not sys.stdin:
        f.close()

    print("SUMMARY:")
    for pair, nums in cumulative.items():
        print(f"{pair:<10} sum: {nums['sum']:>12.4f} {nums['amount']:>12.4f}")

    if False:
        print(f"Pairs:")
        print(f"Types:")
        print(f"Costs: {','.join(costs)}")

if __name__ == "__main__":
    sys.exit(main())
