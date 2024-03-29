# created: 2018-12-01
# see 'parser' for expected command-line arguments

# goal: be FAST!!!

''' to test, run something like:

python3 compare_inventories.py inventory-files_do-not-add-to-git/2018-12-01-mba.jsonl inventory-files_do-not-add-to-git/2018-12-03-mba.jsonl > /tmp/out
python3 compare_inventories.py inventory-files_do-not-add-to-git/2018-12-01-imac-pro.jsonl inventory-files_do-not-add-to-git/2018-12-29-imac-pro.jsonl > /tmp/out
python3 compare_inventories.py inventory-files_do-not-add-to-git/2018-12-15-imac-pro.jsonl inventory-files_do-not-add-to-git/2018-12-29-imac-pro.jsonl > /tmp/out

TODOs:
- use heuristics like file size and modtimes to see if those files were MOVED
'''

# include slashes in dirnames to prevent spurious substring matches
DEFAULT_IGNORE_DIRS = ['directory-tree-inventory/inventory-files_do-not-add-to-git',
                       '/.git',
                       '/node_modules',
                       '/.dropbox.cache']

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

    # key: crc32 hash value, value: list of records with this hash
    records_by_crc32 = defaultdict(list)

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

        try:
            crc32_val = record['crc32']
            records_by_crc32[crc32_val].append(record)
        except KeyError:
            pass

    # clean up metadata
    metadata['dt'] = datetime.datetime.utcfromtimestamp(metadata['ts']).strftime('%Y-%m-%d %H:%M:%S UTC')
    del metadata['ts']
    if not metadata['ignore_dirs']:
        del metadata['ignore_dirs']

    ret['metadata'] = metadata
    ret['records_by_path'] = records_by_path
    ret['records_by_modtime'] = records_by_modtime
    ret['records_by_filesize'] = records_by_filesize
    if records_by_crc32:
        ret['records_by_crc32'] = records_by_crc32

    assert len(records_by_path) == n_records
    assert sum(len(e) for e in records_by_modtime.values()) == n_records
    assert sum(len(e) for e in records_by_filesize.values()) == n_records
    return ret


# create a tree-like structure from a list of files, each one containing
# a 'dirs' entry which is a list of directory path entries for that file
def create_dirtree(files_lst):
    rootdir = dict(files=[],
                   subdirs={}, # key: name of one subdirectory level, value: its entry
                   dirname='')
    for e in files_lst:
        path_entries = e['dirs']
        if len(path_entries) == 1 and path_entries[0] == '': # top-level root dir
            rootdir['files'].append(e)
        else:
            cur_entry = rootdir # always start at root

            # traverse down path_entries and create children to the tree
            # rooted at rootdir as necessary:
            for p in path_entries:
                if p not in cur_entry['subdirs']:
                    cur_entry['subdirs'][p] = dict(dirname=p, files=[], subdirs={})
                cur_entry = cur_entry['subdirs'][p]
            cur_entry['files'].append(e)
    return rootdir


# dt: created by create_dirtree
def pretty_print_dirtree(dt, summary_threshold, aux_dict_repr):
    def print_helper(cur_entry, level):
        prefix = ('    ' * level)
        prefix_plus_one = ('    ' * (level+1))
        print(prefix + '/' + cur_entry['dirname']) # leading '/' for readability
        n_files = len(cur_entry['files'])
        if n_files > summary_threshold:
            print(f'{prefix_plus_one}[{n_files} files]')
        else:
            for f in cur_entry['files']:
                print(f'{prefix_plus_one}{f["fn"]}    {aux_dict_repr(f)}')
        for k in sorted(cur_entry['subdirs'].keys()):
            print_helper(cur_entry['subdirs'][k], level+1)

    print_helper(dt, 0)


# compare inventories produced by parse_inventory_file
# you can pass in optional paths to ignore
def compare_inventories(first, second, summary_threshold,
                        ignore_modtimes=False,
                        ignore_dirs=[],
                        ignore_filenames=[],
                        ignore_exts=[],
                        ignore_direxts=[]):
    # make sure they start as empty lists
    if not ignore_dirs: ignore_dirs = []
    if not ignore_filenames: ignore_filenames = []
    if not ignore_exts: ignore_exts = []
    if not ignore_direxts: ignore_direxts = []

    # append defaults:
    ignore_dirs += DEFAULT_IGNORE_DIRS
    ignore_filenames += DEFAULT_IGNORE_FILENAMES
    ignore_direxts += DEFAULT_IGNORE_DIREXTS

    # parse it:
    ignore_direxts = [tuple(e.split(',')) for e in ignore_direxts]
    for e in ignore_direxts: assert len(e) == 2

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

        ext = os.path.splitext(e[1])[1].lower() # extension - LOWERCASE IT for simplicity
        if ext in ignore_exts:
            return True

        # simultaneously match both a directory (e[0]) and an extension
        if (e[0], ext) in ignore_direxts:
            return True

        return False


    print(f'ignore_dirs: {ignore_dirs}\nignore_filenames: {ignore_filenames}\nignore_exts: {ignore_exts}\nignore_direxts: {ignore_direxts}\nsummary_threshold: {summary_threshold}')
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

    changed_files = []
    # for files in both first and second, compare their metadata
    for e in in_both:
        first_data = first_rbp[e]
        second_data = second_rbp[e]

        if should_ignore(e):
            continue

        modtimes_differ = False
        modtimes_diff_secs = 0
        sizes_differ = False
        sizes_diff_bytes = 0

        # use a heuristic for 'close enough' in terms of modtimes
        # (within a minute)
        if not ignore_modtimes:
            modtimes_diff_secs = round(second_data['mt'] - first_data['mt'])
            if abs(modtimes_diff_secs) > 60:
                modtimes_differ = True

        if first_data['sz'] != second_data['sz']:
            sizes_differ = True
            sizes_diff_bytes = second_data['sz'] - first_data['sz']

        # only report a change if the SIZE differs
        # (note that there may be false positives ... use a has to be
        # really sure!!!)
        #if modtimes_differ or sizes_differ:
        if sizes_differ:
            assert len(e) == 2
            changed_files.append(dict(dirs=e[0].split('/'), fn=e[1], diff_secs=modtimes_diff_secs, diff_bytes=sizes_diff_bytes))

    changed_tree = create_dirtree(changed_files)
    print('files changed ...')
    #print(json.dumps(changed_tree))

    def changed_repr(f):
        delta_bytes = None
        if f["diff_bytes"] > 0:
            delta_bytes = f'+{f["diff_bytes"]} bytes'
        elif f["diff_bytes"] < 0:
            delta_bytes = f'{f["diff_bytes"]} bytes'
        else:
            delta_bytes = 'NO SIZE CHANGE'
        return f'({str(datetime.timedelta(seconds=f["diff_secs"]))}, {delta_bytes})'

    pretty_print_dirtree(changed_tree, summary_threshold, changed_repr)


    def plain_repr(f):
        return f'({f["size"]} bytes, modtime: {int(f["modtime"])})'

    first_rbs = first['records_by_filesize']
    second_rbs = second['records_by_filesize']

    print('\nonly in first ...')
    only_first_files = []
    for e in sorted(in_first_but_not_second):
        if not should_ignore(e):
            assert len(e) == 2
            only_first_files.append(dict(dirs=e[0].split('/'), fn=e[1], size=first_rbp[e]['sz'], modtime=first_rbp[e]['mt']))
    only_first_tree = create_dirtree(only_first_files)
    pretty_print_dirtree(only_first_tree, summary_threshold, plain_repr)

    print('\nonly in second ...')
    only_second_files = []
    for e in sorted(in_second_but_not_first):
        if not should_ignore(e):
            assert len(e) == 2
            only_second_files.append(dict(dirs=e[0].split('/'), fn=e[1], size=second_rbp[e]['sz'], modtime=second_rbp[e]['mt']))
    only_second_tree = create_dirtree(only_second_files)
    pretty_print_dirtree(only_second_tree, summary_threshold, plain_repr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # mandatory positional arguments:
    parser.add_argument("first_file", help="first inventory file to compare")
    parser.add_argument("second_file", help="second inventory file to compare")
    parser.add_argument("--ignore_modtimes", help="ignore modification times", action="store_true")
    parser.add_argument("--ignore_dirs", nargs='+', help="ignore the following directories: <list>")
    parser.add_argument("--ignore_files", nargs='+', help="ignore the following filenames: <list>")
    parser.add_argument("--ignore_exts", nargs='+', help="ignore the following file extensions: <list>")
    parser.add_argument("--ignore_direxts", nargs='+', help="ignore the following file extensions within directories: <list> of entries, each being 'dirname,extension'")
    parser.add_argument("--summary_threshold", action='store', help="summarize a directory when it has more than N files")

    args = parser.parse_args()
    first = parse_inventory_file(args.first_file)
    second = parse_inventory_file(args.second_file)
    compare_inventories(first, second,
                        int(args.summary_threshold) if args.summary_threshold else DEFAULT_SUMMARY_THRESHOLD, # argh!!!
                        args.ignore_modtimes,
                        args.ignore_dirs, args.ignore_files,
                        args.ignore_exts, args.ignore_direxts)
