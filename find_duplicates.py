# created: 2019-02-10
# see 'parser' for expected command-line arguments

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from compare_inventories import parse_inventory_file, DEFAULT_IGNORE_FILENAMES, DEFAULT_IGNORE_DIRS

# requires python >= 3.5 to get os.walk to use the MUCH faster os.scandir function
assert float(sys.version[:3]) >= 3.5

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # mandatory positional arguments:
    parser.add_argument("inventory_file", help="inventory file in which to find duplicates")

    args = parser.parse_args()
    inv = parse_inventory_file(args.inventory_file)

    rbcrc = inv['records_by_crc32']

    for k, v in rbcrc.items(): # in py3, items() is an iterator
        if len(v) > 1:
            entries_by_size = defaultdict(list)
            for e in v:
                if e['f'] not in DEFAULT_IGNORE_FILENAMES:
                    for d in DEFAULT_IGNORE_DIRS:
                        if d in e['d']:
                            break # get out and don't run the 'else' clause
                    else:
                        entries_by_size[e['sz']].append(e)
            for sz, possible_dups in entries_by_size.items():
                if len(possible_dups) > 1:
                    for pd in possible_dups:
                        print(os.path.join(pd['d'], pd['f']))
                    print()
