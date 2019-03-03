# created: 2019-02-10
# see 'parser' for expected command-line arguments

# goal: be FAST!!!

# include slashes in dirnames to prevent spurious substring matches
IGNORE_DIRS = ['directory-tree-inventory/inventory-files_do-not-add-to-git',
               '/.git',
               '/node_modules',
               '/.dropbox.cache']

IGNORE_FILENAMES = ['Thumbs.db', 'thumbs.db', '.DS_Store', 'Icon\r'] # 'Icon\r' doesn't print properly anyhow, #weird

DEFAULT_SUMMARY_THRESHOLD = 10


import argparse
import json
import os
import sys
import time
import datetime
from collections import Counter, defaultdict
from compare_inventories import parse_inventory_file, pretty_print_dirtree

# requires python >= 3.5 to get os.walk to use the MUCH faster os.scandir function
assert float(sys.version[:3]) >= 3.5

def find_needle_in_haystack(needle, haystack):
    needle_rbp = needle['records_by_path']
    haystack_rbp = haystack['records_by_path']

    needle_rbcrc = needle['records_by_crc32']
    haystack_rbcrc = haystack['records_by_crc32']

    # starting in March 2019, use crc32 checksums to do a more accurate search
    for k, v in needle_rbcrc.items(): # in py3, items() is an iterator
        if k not in haystack_rbcrc: # can't find this needle's hash in haystack
            for e in v:
                if e['f'] not in IGNORE_FILENAMES:
                    print(e)

    # old path-based algorithm as of Feb 2019
    '''
    haystack_file_basenames_to_entries = defaultdict(list)
    for k in haystack_rbp:
        haystack_file_basenames_to_entries[k[-1]].append(haystack_rbp[k])

    for k in needle_rbp:
        needle_entry = needle_rbp[k]
        bn = k[-1]
        try:
            haystack_entries = haystack_file_basenames_to_entries[bn]
            if not haystack_entries:
                print(os.path.join(*k), 'NOT in haystack')
            else:
                sz = needle_entry['sz']
                match_found = False
                for e in haystack_entries:
                    if e['sz'] == sz:
                        match_found = True
                        break
                if not match_found:
                    print(os.path.join(*k), 'in haystack but DIFFERENT SIZE')
        except KeyError:
            print(os.path.join(*k), 'NOT in haystack')
    '''

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # mandatory positional arguments:
    parser.add_argument("needle_file", help="inventory file to use as the 'needles' to find in haystack")
    parser.add_argument("haystack_file", help="inventory file to use as haystack")

    args = parser.parse_args()
    needle = parse_inventory_file(args.needle_file)
    haystack = parse_inventory_file(args.haystack_file)
    find_needle_in_haystack(needle, haystack)
