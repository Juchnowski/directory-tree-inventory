# created: 2018-12-01
# see 'parser' for expected command-line arguments

# goal: be FAST!!!

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


# compare inventories produced by parse_inventory_file
# you can pass in optional directories, filenames, and file extensions to ignore
def compare_inventories(first, second,
                        ignore_dirs=[], ignore_filenames=[], ignore_exts=[]):
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
        if first_data['mt'] != second_data['mt']:
            print(e, 'modtimes differ')
        if first_data['sz'] != second_data['sz']:
            print(e, 'sizes differ')


    # TODO: for files in_first_but_not_second and in_second_but_not_first,
    # use heuristics to determine whether those files have been MOVED


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # mandatory positional arguments:
    parser.add_argument("first_file", help="first inventory file to compare")
    parser.add_argument("second_file", help="second inventory file to compare")

    args = parser.parse_args()
    first = parse_inventory_file(args.first_file)
    second = parse_inventory_file(args.second_file)
    compare_inventories(first, second)
