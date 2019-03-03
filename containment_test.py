# created: 2019-02-10
# see 'parser' for expected command-line arguments

# goal: be FAST!!!

''' to test, run something like:

python3 containment_test.py inventory-files_do-not-add-to-git/2019-03-02-imac-pro-old-backup-archives.jsonl inventory-files_do-not-add-to-git/2019-03-02-imac-pro-dropbox.jsonl

NB:
- there's a lot of old website backups in here that i haven't picked up
  on, and maybe some old email backups too

TODOs:
- include a good set of ignores for dirs/files
'''

# include slashes in dirnames to prevent spurious substring matches
DEFAULT_IGNORE_DIRS = ['directory-tree-inventory/inventory-files_do-not-add-to-git',
                       '/.git',
                       '/node_modules',
                       '.dropbox.cache/']

DEFAULT_IGNORE_FILENAMES = ['Thumbs.db', 'thumbs.db', '.DS_Store', 'Icon\r'] # 'Icon\r' doesn't print properly anyhow, #weird

DEFAULT_IGNORE_DIREXTS = ['pgbovine,.htm', 'pgbovine,.html']

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

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # mandatory positional arguments:
    parser.add_argument("needle_file", help="inventory file to use as the 'needles' to find in haystack")
    parser.add_argument("haystack_file", help="inventory file to use as haystack")
    parser.add_argument("--ignore_dirs", nargs='+', help="ignore the following directories: <list>")
    parser.add_argument("--ignore_files", nargs='+', help="ignore the following filenames: <list>")
    parser.add_argument("--ignore_exts", nargs='+', help="ignore the following file extensions: <list>")
    parser.add_argument("--ignore_direxts", nargs='+', help="ignore the following file extensions within directories: <list> of entries, each being 'dirname,extension'")

    args = parser.parse_args()
    needle = parse_inventory_file(args.needle_file)
    haystack = parse_inventory_file(args.haystack_file)
    find_needle_in_haystack(needle, haystack)
