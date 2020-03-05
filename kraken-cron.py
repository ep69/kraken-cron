#!/usr/bin/env python3

# Buy BTC for EUR on kraken.com

import sys
import requests
import json
import krakenex

INVEST_EUR = 1 # TODO
BTC_MIN = 0.002 # minimum amount of BTC to buy

k = krakenex.API()
k.load_key('kc.key')

def get_price():
    url = "https://api.kraken.com/0/public/Ticker?pair=XBTEUR"
    response = requests.get(url)
    data = json.loads(response.text)
    print(f"Retuned data: {data}")
    for k in data:
        print(f"Key '{k}' value '{data[k]}'")
    return data["result"]["XXBTZEUR"]["c"][0]


def get_ballance_eur():
    data = k.query_private('Balance')
    print(f"Retuned data: {data}")
    eur = float(data['result']['ZEUR'])
    print(f"Balance {eur} eur")
    return eur


def buy_btc(amount):
    #amount = 0.001 # TODO
    print(f"Want to buy {amount} btc")
    data  = k.query_private('AddOrder', {'pair':'XXBTZEUR', 'type':'buy', 'ordertype':'market', 'leverage':'none', 'volume':str(amount)})
    print(f"Retuned data: {data}")


price = float(get_price())
print(f"Price: {price}")
btc = max(INVEST_EUR / price, BTC_MIN)
print(f"Invest {INVEST_EUR} eur => buy {btc} btc")

eur = get_ballance_eur()
if eur < 2*INVEST_EUR:
    print("Error - no enough EUR")
    sys.exit(1)

buy_btc(btc)
