#!/usr/bin/env python3

# extract daily data
# for a in *.zip; do for f in $(unzip -l $a |grep '1440.csv' |awk '{ print $NF }'); do echo $f; unzip -p $a $f >$f; done; done

import sys
import os
import csv
from datetime import datetime
from decimal import Decimal

import util

def parse(args):
    files = args
    result = {}
    for f in files:
        name = os.path.basename(f).split("_")[0]
        base, quote = util.parse_pair(name)
        print(f"{name} -> {base} {quote}")
        result[name] = {"path": f}
    return result

def main():

    # read and parse the data
    data = {}
    dates = set()
    cryptos = set()
    pairs = set()
    for path in sys.argv[1:]:
        pair = os.path.basename(path).split("_")[0]
        pair = util.official_pair(pair)
        pairs |= set((pair,))
        base, quote = util.parse_pair(pair)
        cryptos |= set((base,))
        print(f"{pair} -> {base} {quote}")
        with open(path, "r") as f:
            reader = csv.DictReader(f, ["seconds", "open", "high", "low", "close", "volume", "count"])
            data[pair] = {}
            n = 0
            for row in reader:
                n +=1
                day = datetime.fromtimestamp(int(row["seconds"])).strftime("%F")
                dates |= set((day,))
                high = Decimal(row["high"])
                low = Decimal(row["low"])
                close = Decimal(row["close"])
                avg = (high + low + close) / 3
                data[pair][day] = avg
                #if n >10:
                #    break
    #print(data)
    dates_sorted = sorted(dates)
    print(f"Start date: {dates_sorted[0]}")
    print(f"Cryptos : {', '.join(cryptos)}")

    official_pairs = [util.official_pair(pair) for pair in pairs]
    print(f"Pairs : {', '.join(official_pairs)}")

    # merge the data
    OUT_FILE = "fiat_pairs.csv"

    fields = ["day"] + list(official_pairs)
    with open(OUT_FILE, "w") as f:
        writer = csv.DictWriter(f, fields)
        writer.writeheader()

        for day in dates_sorted:
            row = {}
            row["day"] = day
            for pair in pairs:
                if day in data[pair]:
                    row[pair] = f"{data[pair][day]:.4f}"
            writer.writerow(row)

    #print(inputs)



if __name__ == "__main__":
    sys.exit(main())
