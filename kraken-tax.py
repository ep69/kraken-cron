#!/usr/bin/env python3

import sys
import argparse
import logging
import datetime

import csv
from pprint import pformat
from decimal import Decimal
from collections import deque

import util
from util import error, warn, info, debug, set_verbose

def rstring(row):
    base, quote = util.parse_pair(row["pair"])
    return f"{row['time'].split()[0]} {row['type']:<4} {float(row['vol']):>11.4f} {base:<5} for {float(row['cost']):>10.4f} {quote:<5} (price {float(row['price']):>10.4f}, fee {float(row['fee']):>9.6f}) ({row['pair']})"

class TaxMethod:
    def __init__(self, name, skip_crypto_crypto=False, price_data=None):
        self.name = name
        self.cc = not skip_crypto_crypto
        if not price_data:
            price_data = util.price_data()
        self.price_data = price_data

    def handle(self, typ, day, base, quote, vol, cost, fee):
        if typ not in ("buy", "sell"):
            error(f"Unknown type: {typ}")
        pair = util.official_pair(base + quote)

        if util.is_fiat(quote):
            if typ == "buy":
                self.buy(day, base, quote, vol, cost, fee)
            else: # sell
                self.sell(day, base, quote, vol, cost, fee)
        elif util.is_crypto(quote) and self.cc:
            if typ == "buy":
                # buy for cc means selling quote and buying base
                pair_quote = quote + self.currency
                pair_base = base + self.currency
                price_quote = self.price_data[day][pair_quote]
                price_base = self.price_data[day][pair_base]
                vol_sell = cost
                vol_buy = vol
                cost_sell = vol_sell * price_quote
                cost_buy = vol_buy * price_base
                fee_total = fee * price_quote
                fee_sell = fee_total / 2
                fee_buy = fee_total - fee_sell
                debug(f"FAKE sell: {day} {vol_sell:.2f} {quote} for {cost_sell:.2f} {self.currency} (price {cost_sell/vol_sell:.2f}) fee {fee_sell:.2f} /{pair}")
                self.sell(day, quote, self.currency, vol_sell, cost_sell, fee_sell, profit_pair=pair)
                debug(f"FAKE buy: {day} {vol_buy:.2f} {base} for {cost_buy:.2f} {self.currency} (price {cost_buy/vol_buy:.2f}) fee {fee_buy:.2f}")
                self.buy(day, base, self.currency, vol_buy, cost_buy, fee_buy)
            else: # sell
                # sell for cc means selling base and buying quote
                pair_quote = quote + self.currency
                pair_base = base + self.currency
                price_quote = self.price_data[day][pair_quote]
                price_base = self.price_data[day][pair_base]
                vol_sell = vol
                vol_buy = cost
                cost_sell = vol_sell * price_base
                cost_buy = vol_buy * price_quote
                fee_total = fee * price_quote
                fee_sell = fee_total / 2
                fee_buy = fee_total - fee_sell
                debug(f"FAKE sell: {day} {vol_sell:.2f} {base} for {cost_sell:.2f} {self.currency} (price {cost_sell/vol_sell:.2f}) fee {fee_sell:.2f} /{pair}")
                self.sell(day, base, self.currency, vol_sell, cost_sell, fee_sell, profit_pair=pair)
                debug(f"FAKE buy: {day} {vol_buy:.2f} {quote} for {cost_buy:.2f} {self.currency} (price {cost_buy/vol_buy:.2f}) fee {fee_buy:.2f}")
                self.buy(day, quote, self.currency, vol_buy, cost_buy, fee_buy)
        elif util.is_crypto(quote) and not self.cc:
            debug(f"{self.name}: skipping CC {base} / {quote}")
            pass
        else:
            error(f"Unknown situation")

    def buy(self, day, base, quote, vol, cost, fee):
        error("Not implemented (buy)")

    def sell(self, day, base, quote, vol, cost, fee, profit_pair=None):
        error("Not implemented (sell)")

class WeightedAverage(TaxMethod):
    def __init__(self, name, skip_crypto_crypto=False, profit_currency="ZEUR"):
        super().__init__(name, skip_crypto_crypto=skip_crypto_crypto)
        self.currency = util.official_currency(profit_currency)
        self.data = {}

    def init_pair(self, pair):
        base, quote = util.official_parse(pair)

        # for profit pairs, quote != profit currency
        if util.is_crypto(quote):
            currency = self.currency
        else:
            currency = quote

        self.data[pair] = {
            "cost": Decimal(0),
            "amount": Decimal(0),
            "fees": Decimal(0),
            "profits": {},
            "currency": currency,
        }

    def buy(self, day, base, quote, vol, cost, fee):
        pair = base + quote
        if pair not in self.data:
            self.init_pair(pair)

        self.data[pair]["amount"] += vol
        self.data[pair]["cost"] += cost
        self.data[pair]["fees"] += fee

        avg_price = self.data[pair]["cost"] / self.data[pair]["amount"]
        amount = self.data[pair]["amount"]
        cost = self.data[pair]["cost"]
        fees = self.data[pair]["fees"]
        debug(f"buy cummulative values: {pair} {amount:.2f} {base}, cost {cost:.2f}, avg_price {avg_price:.2f}, fees {fees:.2f}") 

    def sell(self, day, base, quote, vol, cost, fee, profit_pair=None):
        pair = base + quote
        if pair not in self.data:
            self.init_pair(pair)

        if self.data[pair]["amount"] > Decimal(0):
            amount = self.data[pair]["amount"]
            if vol > amount:
                print(f"{pair} vol {vol} amount {amount}")
                warn(f"Corner case {pair} - we did not buy enough to sell {vol:>6.2f} > {amount:>6.2f}, missing {vol-amount:>11.4f} {util.human_currency(base)}")
                buy_vol = amount
            else:
                buy_vol = vol
            avg_price = self.data[pair]["cost"] / amount
            avg_fee = self.data[pair]["fees"] / amount
            buy_cost = buy_vol * avg_price
            # TODO is buy-fee included in cost, or extra?
            buy_fee = buy_vol * avg_fee
            self.data[pair][f"amount"] -= buy_vol
            self.data[pair][f"cost"] -= buy_cost
            self.data[pair][f"fees"] -= buy_fee
            #print(f"avg_price {avg_price:.2f} avg_fee {avg_fee:.2f}")
        else: # selling something not owned => no past expenses
            buy_cost = Decimal(0)
            buy_fee = Decimal(0)

        profit = cost - buy_cost - buy_fee - fee # sell-fee

        year = int(day[:4])
        if not profit_pair:
            profit_pair = pair
        if profit_pair not in self.data:
            self.init_pair(profit_pair)
        if year not in self.data[profit_pair]["profits"]:
            self.data[profit_pair]["profits"][year] = Decimal(0)
        self.data[profit_pair]["profits"][year] += profit

class Filter:
    def match(self, typ, day, base, quote, vol, cost, fee):
        error(f"Filter not implemented")

class FilterOnlyBTCEUR(Filter):
    def __init__(self):
        self.name = "btceur"

    def match(self, typ, day, base, quote, vol, cost, fee):
        return base not in ("XBT", "XXBT") or quote not in ("EUR", "ZEUR")

def main():
    last_year = int(datetime.datetime.now().date().strftime("%Y")) - 1
    INFILE = "trades.csv"
    PROFIT_CURRENCY = "EUR"
    TAX_CURRENCY = "CZK"
    TAX_DEFAULT = 15

    FILTERS = []
    btceur = FilterOnlyBTCEUR()
    FILTERS = [btceur]

    ap = argparse.ArgumentParser(description="Compute taxes")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="verbose - print debug messages")
    ap.add_argument("-i", "--infile", default=INFILE,
                    help="verbose - print debug messages")
    ap.add_argument("-y", "--year", default=last_year,
                    help="tax year, last year by default")
    ap.add_argument("--profit-currency", default=PROFIT_CURRENCY,
                    help=f"fiat currency for crypto-crypto trades, default {PROFIT_CURRENCY}")
    ap.add_argument("-t", "--tax", default=TAX_DEFAULT,
                    help=f"tax percents, default {TAX_DEFAULT}")
    ap.add_argument("--tax-currency", default=TAX_CURRENCY,
                    help=f"tax currency, default {TAX_CURRENCY}")
    ap.add_argument("-m", "--method", action="append", dest="methods",
                    help=f"methods to use, default is all")
    ap.add_argument("-f", "--filter", action="append", dest="filters",
                    help=f"Available filters: {', '.join(f.name for f in FILTERS)}; default is none")

    args = ap.parse_args()

    if args.verbose:
        set_verbose()

    infile = args.infile
    if infile == "-":
        infile = None

    tax_year = int(args.year)
    tax = Decimal(0.01) * Decimal(args.tax)
    tax_currency = args.tax_currency
    profit_currency = args.profit_currency

    METHODS = []
    wa_simple = WeightedAverage("WAsimple", skip_crypto_crypto=True, profit_currency=profit_currency)
    wa_full = WeightedAverage("WA", skip_crypto_crypto=False, profit_currency=profit_currency)
    METHODS = [wa_simple, wa_full]

    method_names = args.methods
    methods = []

    if method_names:
        debug(f"Method names: {method_names}")
        for m in METHODS:
            if m.name in method_names:
                debug(f"Method to use: {m.name}")
                methods.append(m)
            else:
                debug(f"Method '{m.name}' NOT in {method_names}")
    if not methods:
        debug(f"No methods, using all")
        methods = METHODS

    filters = []
    if not args.filters:
        debug(f"No filters")
    else:
        for f in FILTERS:
            if f.name in args.filters:
                filters.append(f)
        debug(f"Resulting filters: {', '.join(f.name for f in filters)}")

    if infile:
        debug(f"Opening {infile}")
        fi = open(infile, mode="r")
    else: # use stdin
        fi = sys.stdin

    reader = csv.DictReader(fi)

    n = 0
    for row in reader:
        n += 1
        if n == 1: # header
            debug(f"Columns: {', '.join(row.keys())}")

        debug(rstring(row))

        pair = util.official_pair(row["pair"])
        base, quote = util.official_parse(pair)

        typ = row["type"]
        day = row["time"][:10]
        cost = Decimal(row["cost"])
        vol = Decimal(row["vol"])
        fee = Decimal(row["fee"])

        skip = False
        for filt in filters:
            if filt.match(typ, day, base, quote, vol, cost, fee):
                debug(f"Filter {filt.name} matched: {typ} {day} {base} {quote} {vol} {cost} {fee}")
                skip = True
                break
        if skip:
            info(f"Skipping: {typ} {day} {base} {quote} {vol} {cost} {fee}")
            continue

        for m in methods:
            m.handle(typ, day, base, quote, vol, cost, fee)

    if fi is not sys.stdin:
        fi.close()

    forex_prices = util.forex_data()

    for m in methods:
        info(f"\n{m.name}:")
        total = {}
        for pair, vals in m.data.items():
            currency = util.human_currency(vals["currency"])
            if currency not in total:
                total[currency] = Decimal(0)
            profit = Decimal(0)
            if tax_year in vals["profits"]:
                profit = vals["profits"][tax_year]
            if profit:
                base, quote = (util.human_currency(c) for c in util.parse_pair(pair))
                total[currency] += profit
                info(f"    {base:<4} / {quote:<4} {tax_year} profit {profit:>12.2f} {currency}")
        info(f"  PROFITS:")
        tax_base = Decimal(0)
        for k, v in total.items():
            if not v:
                continue
            debug(f"k {k} tc {tax_currency}")
            p = util.human_currency(k) + util.human_currency(tax_currency)
            tax_sub = forex_prices[tax_year][p] * v
            tax_base += tax_sub
            info(f"{tax_sub:>20.2f} {tax_currency}  <-  {v:>10.2f} {k}")
        info(f"  TOTAL: {tax_base:>11.2f} {tax_currency}")
        tax_total = tax_base * tax
        info(f"  TAX: {tax_total:>13.2f} {tax_currency}")

if __name__ == "__main__":
    sys.exit(main())
