import sys
import csv
from decimal import Decimal

def error(m):
    print(f"ERROR: {m}")
    sys.exit(1)

known_crypto = ("XLM", "XBT", "XMR", "BCH", "ETH", "NANO", "LTC", "REPV2", "EOS", "XDG", "XRP", "UNI", "USDT")
known_fiat = ("EUR", "USD")

def is_crypto(c):
    return c in known_crypto or c.startswith("X") and c[1:] in known_crypto

def is_fiat(c):
    return c in known_fiat or c.startswith("Z") and c[1:] in known_fiat

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

def official_currency(c):
    prefix = ""
    if c in known_crypto:
        prefix = "X"
    elif c in known_fiat:
        prefix = "Z"
    elif c[0] == "X" and c[1:] in known_crypto:
        pass
    elif c[0] == "Z" and c[1:] in known_fiat:
        pass
    else:
        error(f"official_currency {c} problem")
    return prefix + c


def official_pair(pair):
    base, quote = parse_pair(pair)
    return official_currency(base) + official_currency(quote)

def price_data():
    data = {}
    with open("data/fiat_pairs.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            print(row)
            day = row["day"]
            prices = {}
            for k, v in row.items():
                if k != "day":
                    if v:
                        prices[k] = Decimal(v)
                    else:
                        prices[k] = None
            data[day] = prices
    return data

