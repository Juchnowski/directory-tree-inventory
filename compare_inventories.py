# created: 2018-12-01
# see 'parser' for expected command-line arguments

# goal: be FAST!!!

''' to test, run something like:

python3 compare_inventories.py inventory-files_do-not-add-to-git/2018-12-01-mba.jsonl inventory-files_do-not-add-to-git/2018-12-03-mba.jsonl > /tmp/out

'''

import argparse
import json
import os
import sys
import time
from datetime import datetime
from collections import Counter, defaultdict

# requires python >= 3.5 to get os.walk to use the MUCH faster os.scandir function
assert float(sys.version[:3]) >= 3.5

# parses an inventory file created by create_inventory() in create_inventory.py
# and returns a dict
def parse_inventory_file(filename):
    ret = {}

    assert os.path.isfile(filename)
    metadata = None

    # index the records in a few ways
    records_by_path = {} # key: (dirname, filename) tuple

    # key: modtime, value: list of records with this modtime
    records_by_modtime = defaultdict(list)

    # key: file size, value: list of records with this file size
    records_by_filesize = defaultdict(list)

    n_records = 0
    for line in open(filename):
        record = json.loads(line)
        # first line is metadata
        if not metadata:
            metadata = record
            continue # ok, next!

        n_records += 1

        dn = record['d']
        fn = record['f']
        ext = record['e']
        modtime = record['mt']
        filesize = record['sz']

        assert (dn, fn) not in records_by_path
        records_by_path[(dn, fn)] = record

        records_by_modtime[modtime].append(record)
        records_by_filesize[filesize].append(record)

    # clean up metadata
    metadata['dt'] = datetime.utcfromtimestamp(metadata['ts']).strftime('%Y-%m-%d %H:%M:%S UTC')
    del metadata['ts']
    if not metadata['ignore_dirs']:
        del metadata['ignore_dirs']

    ret['metadata'] = metadata
    ret['records_by_path'] = records_by_path
    ret['records_by_modtime'] = records_by_modtime
    ret['records_by_filesize'] = records_by_filesize

    assert len(records_by_path) == n_records
    assert sum(len(e) for e in records_by_modtime.values()) == n_records
    assert sum(len(e) for e in records_by_filesize.values()) == n_records
    return ret


# include slashes in dirnames to prevent spurious substring matches
DEFAULT_IGNORE_DIRS = ['directory-tree-inventory/inventory-files_do-not-add-to-git',
                       '/.git',
                       '/node_modules',
                       '.dropbox.cache/']

DEFAULT_IGNORE_FILENAMES = ['.DS_Store']
DEFAULT_IGNORE_EXTS = []


# compare inventories produced by parse_inventory_file
# you can pass in optional directories, filenames, and file extensions to ignore
def compare_inventories(first, second,
                        ignore_modtimes=False,
                        ignore_dirs=[],
                        ignore_filenames=[],
                        ignore_exts=[]):
    # make sure they start as empty lists
    if not ignore_dirs: ignore_dirs = []
    if not ignore_filenames: ignore_filenames = []
    if not ignore_exts: ignore_exts = []

    # append defaults:
    ignore_dirs += DEFAULT_IGNORE_DIRS
    ignore_filenames += DEFAULT_IGNORE_FILENAMES
    ignore_exts += DEFAULT_IGNORE_EXTS

    # make sure extensions start with '.'!
    for e in ignore_exts:
        assert e[0] == '.'


    # e is a (dirname, filename) pair
    def should_ignore(e):
        for d in ignore_dirs:
            if d in e[0]: # substring match
                return True
        if e[1] in ignore_filenames:
            return True

        ext = os.path.splitext(e[1])[1] # extension
        if ext in ignore_exts:
            return True

        return False


    print(f'ignore_dirs: {ignore_dirs}\nignore_filenames: {ignore_filenames}\nignore_exts: {ignore_exts}')
    print('---')
    print('First: ', first['metadata'])
    print('Second:', second['metadata'])
    print('---')

    first_rbp = first['records_by_path']
    second_rbp = second['records_by_path']

    first_rbp_keys = set(first_rbp.keys())
    second_rbp_keys = set(second_rbp.keys())

    in_first_but_not_second = first_rbp_keys.difference(second_rbp_keys)
    in_second_but_not_first = second_rbp_keys.difference(first_rbp_keys)
    in_both = first_rbp_keys.intersection(second_rbp_keys)
    print(len(first_rbp_keys), len(second_rbp_keys))
    print(len(in_first_but_not_second), len(in_second_but_not_first), len(in_both))

    # for files in both first and second, compare their metadata
    for e in in_both:
        first_data = first_rbp[e]
        second_data = second_rbp[e]

        if should_ignore(e):
            continue

        # use a heuristic for 'close enough' in terms of modtimes
        # (within a minute)
        if not ignore_modtimes:
            if abs(first_data['mt'] - second_data['mt']) > 60:
                print(e, f"modtimes differ by {round(abs(first_data['mt'] - second_data['mt']))} seconds")

        if first_data['sz'] != second_data['sz']:
            print(e, 'sizes differ:', first_data['sz'], second_data['sz'])


    # TODO: for files in_first_but_not_second and in_second_but_not_first,
    # use heuristics to determine whether those files have been MOVED
    print('---\nTODO: use heuristics like file size to see if those files were MOVED')
    print('\nonly in first ...')
    for e in sorted(in_first_but_not_second):
        if not should_ignore(e):
            print(e)
    print('\nonly in second ...')
    for e in sorted(in_second_but_not_first):
        if not should_ignore(e):
            print(e)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # mandatory positional arguments:
    parser.add_argument("first_file", help="first inventory file to compare")
    parser.add_argument("second_file", help="second inventory file to compare")
    parser.add_argument("--ignore_modtimes", help="ignore modification times", action="store_true")
    parser.add_argument("--ignore_dirs", nargs='+', help="ignore the following directories: <list>")
    parser.add_argument("--ignore_files", nargs='+', help="ignore the following filenames: <list>")
    parser.add_argument("--ignore_exts", nargs='+', help="ignore the following file extensions: <list>")

    args = parser.parse_args()
    first = parse_inventory_file(args.first_file)
    second = parse_inventory_file(args.second_file)
    compare_inventories(first, second,
                        args.ignore_modtimes,
                        args.ignore_dirs, args.ignore_files, args.ignore_exts)
