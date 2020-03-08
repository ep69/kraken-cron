#!/bin/bash

# Run kraken-cron.py on CentOS 6 in scl and venv

P="$HOME/kraken-cron" # path to kraken-cron
VENV="$P/venv"

scl enable rh-python36 "bash <<_EOF
  echo -n 'START: '; date
  source $VENV/bin/activate
  python3 $P/kraken-cron.py --dry-run --verbose --buy LTC --sell EUR --amount 10
  deactivate
  echo -n 'END: '; date
_EOF"
