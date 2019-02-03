#!/bin/sh

rm -f /tmp/left.txt /tmp/right.txt
python3 create_inventory.py "$1" left > /tmp/left.txt
python3 create_inventory.py "$2" right > /tmp/right.txt
python3 compare_inventories.py /tmp/left.txt /tmp/right.txt
