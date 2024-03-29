# kraken-cron
Buy crypto coins on kraken.com via API

## Setup
1. Review the code of `kraken-cron.py`. It will be touching your money and other assets. Author does not want to do you any harm, but people make mistakes. Really make sure you know what you are running.
1. Make sure you have python3 installed.
1. Install necessary python modules, `requests` and `krakenex` should be enough for most installations. Example of installing in user home:

        pip install --user requests krakenex
1. Download `kraken-cron.py` script or clone this whole repo:

        wget https://raw.githubusercontent.com/ep69/kraken-cron/master/kraken-cron.py
1. Create API key on kraken.com website and save it to `api.key` file. Format is simply two lines with strings provided by kraken.com.
1. Test the script, e.g.:

        python3 kraken-cron.py --dry-run --verbose
1. If everything looks fine, you can run the script for real.

## Usage
See help:
```
$ ./kraken-cron.py --help
usage: kraken-cron.py [-h] [-k KEY] [-d] [-v] [-a AMOUNT] [-t AMOUNT_TYPE] [-b BUY] [-s SELL] [-c]

Buy coins through Kraken API

optional arguments:
  -h, --help            show this help message and exit
  -k KEY, --key KEY     API key filename (default: api.key in script directory)
  -d, --dry-run         dry run - do not buy anything
  -v, --verbose         verbose - print debug messages
  -a AMOUNT, --amount AMOUNT
                        amount to spend (default: minimum)
  -t AMOUNT_TYPE, --amount-type AMOUNT_TYPE
                        amount type - buy / sell (default: sell)
  -b BUY, --buy BUY     currency to buy (default: BTC)
  -s SELL, --sell SELL  currency to sell (default: EUR)
  -c, --check-balance   check balance before issuing order
```

Note that Kraken imposes a minimum limit per coin and `kraken-cron` will buy this minimum by default.

### Examples
```
# buy minimum BTC amount for EUR
python3 kraken-cron.py --buy BTC
python3 kraken-cron.py # using defaults

# buy specified BTC amount for EUR
python3 kraken-cron.py --buy BTC --sell EUR --amount-type buy --amount X
python3 kraken-cron.py --amount X # using defaults

# buy BTC for specified amount of EUR
python3 kraken-cron.py --buy BTC --sell EUR --amount-type sell --amount X
python3 kraken-cron.py --amount-type sell --amount X # using defaults
```
Use `--dry-run` and `--verbose` arguments any time.


## Bonus: How to run on CentOS 6

Let's say you want to run `kraken-cron.py` as a regular user in cron.

1. As root, install software collections and `rh-python36` package.
1. Switch to the regular user account you want to use.
1. Clone this repo to a directory, e.g., `$HOME/kraken-cron/`.
1. Add kraken keys to a file, e.g., in the default `api.key`
1. In the project directory, create the virtual environment and test the script:

        cd $HOME/kraken-cron
        scl enable rh-python36 bash
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install requests krakenex
        python3 kraken-cron.py --dry-run --verbose
        deactivate
        exit
1. Use `buy6.sh.template` to create your own buying script, adapt the line executing `kraken-cron.py`. Save the resulting file as `buy6.sh`.
1. Let's say you want to execute the buying script every day at 9 AM. Edit your user crontab (`crontab -e`) and add the line:

        0 9 * * * $HOME/kraken-cron/buy6.sh >>$HOME/kraken-cron/kc.log 2>&1
1. Check the log (`$HOME/kraken-cron/kc.log`) to see everything is fine. If so, remove the `--dry-run` argument from the appropriate line in `buy6.sh`.
