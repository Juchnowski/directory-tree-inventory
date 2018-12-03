# created: 2018-12-01
# see 'parser' for expected command-line arguments

# goal: be FAST!!!

'''
TODOs

- allow for a comparison of a directory tree against an existing
  inventory file
- allow for direct comparisons of two directory trees without writing to
  an inventory file
'''

import argparse
import json
import os
import sys
import time
from collections import Counter

# requires python >= 3.5 to get os.walk to use the MUCH faster os.scandir function
assert float(sys.version[:3]) >= 3.5

# which directories NOT to recurse into
# TODO: pass in a custom list as a command-line arg
# (.ptvs is python tools for visual studio)
#DEFAULT_IGNORE_DIRS = ('.git', '.ptvs', 'node_modules')
DEFAULT_IGNORE_DIRS = ()


# creates an inventory starting at rootdir and prints .jsonl result to stdout,
# containing a line for each file's metadata (first line has overall metadata)
def create_inventory(rootdir, label, ignore_dirs=DEFAULT_IGNORE_DIRS):
    assert os.path.isdir(rootdir)

    # first line metadata
    metadata = dict(ts=time.time(), ignore_dirs=ignore_dirs,
                    label=label, rootdir=os.path.abspath(rootdir))
    print(json.dumps(metadata))

    #basename_counter = Counter()
    #extension_counter = Counter()
    #dirnames_counter = Counter()

    for dirpath, dirnames, filenames in os.walk(rootdir, topdown=True):
        # canonicalize dirpath relative to rootdir
        assert dirpath.startswith(rootdir)
        canonical_dirpath = dirpath[len(rootdir):]
        if canonical_dirpath and canonical_dirpath[0] == '/':
            canonical_dirpath = canonical_dirpath[1:]
            assert canonical_dirpath[0] != '/'

        #dirnames_counter[os.path.basename(canonical_dirpath)] += 1

        with os.scandir(dirpath) as it:
            for entry in it:
                if entry.is_file():
                    s = entry.stat()
                    modtime = s.st_mtime # last modification timestamp
                    filesize = s.st_size # how large is this file?

                    base, ext = os.path.splitext(entry.name)
                    #basename_counter[base] += 1
                    #extension_counter[ext] += 1

                    # use short key names to save space :0
                    data = dict(d=canonical_dirpath, f=entry.name,
                                e=ext, mt=modtime, sz=filesize)
                    print(json.dumps(data))

        # from https://docs.python.org/3/library/os.html#os.walk
        # When topdown is True, the caller can modify the dirnames list
        # in-place (perhaps using del or slice assignment), and walk() will
        # only recurse into the subdirectories whose names remain in dirnames;
        # this can be used to prune the search
        for d in ignore_dirs:
            try:
                dirnames.remove(d)
            except ValueError:
                pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # mandatory positional arguments:
    parser.add_argument("root", help="root directory to start inventory crawl")
    parser.add_argument("label", help="label name for this inventory")

    #parser.add_argument("--create", help="create an inventory and write to stdout",
    #                    action="store_true")

    args = parser.parse_args()
    create_inventory(args.root, args.label)
