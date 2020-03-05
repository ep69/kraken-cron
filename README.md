# kraken-cron
Buy BTC on kraken.com via API

## How to use
1. Install python module `krakenex`, e.g.:

        pip install --user krakenex
1. Download `kraken-cron.py` script or clone this whole repo:

        wget https://raw.githubusercontent.com/ep69/kraken-cron/master/kraken-cron.py
1. Create API key on kraken.com and save it to `kc.key` file (format is simply two lines with strings provided by kraken.com).
1. Tweak variables according to your needs, most important `INVEST_EUR`. Note there is a minimum BTC amount to buy and script will try to buy this minimum even if `INVEST_EUR` is lower.
1. Run the script, e.g.:

        python3 kraken-cron.py
