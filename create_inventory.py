# created: 2018-12-01
# see 'parser' for expected command-line arguments

# goal: be FAST!!!

'''
TODOs

- allow for a comparison of a directory tree against an existing
  inventory file
- allow for direct comparisons of two directory trees without writing to
  an inventory file
- compare today's inventory against the last archived entry, and if you
  'accept' the changes, then set today as the most recent archive. this
  way, you can run the script every day interactively as a routine check
- store consecutive inventory files as diffs to save space (optimization)

- add a 'slow mode' that takes the md5 (or other) hash of each file's
  contents, for more accurate diffing at the expense of being slower
  - to make this not as slow, read in only the first N bytes and take a
    super fast hash of it (crc32?)
'''

import argparse
import binascii
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

# don't read too few bytes, or else lots of files look identical due to
# their file type headers being the same
N_BYTES_FOR_CHECKSUM = 100


# creates an inventory starting at rootdir and prints .jsonl result to stdout,
# containing a line for each file's metadata (first line has overall metadata)
def create_inventory(rootdir, label, take_checksum=False, ignore_dirs=DEFAULT_IGNORE_DIRS):
    assert os.path.isdir(rootdir)

    # first line metadata
    metadata = dict(ts=time.time(), ignore_dirs=ignore_dirs,
                    take_checksum=take_checksum, checksum_bytes=N_BYTES_FOR_CHECKSUM,
                    label=label, rootdir=os.path.abspath(rootdir))
    print(json.dumps(metadata))

    for dirpath, dirnames, filenames in os.walk(rootdir, topdown=True):
        # canonicalize dirpath relative to rootdir
        assert dirpath.startswith(rootdir)
        canonical_dirpath = dirpath[len(rootdir):]
        if canonical_dirpath and canonical_dirpath[0] == '/':
            canonical_dirpath = canonical_dirpath[1:]
            assert canonical_dirpath[0] != '/'

        with os.scandir(dirpath) as it:
            for entry in it:
                if entry.is_file():
                    s = entry.stat()
                    modtime = s.st_mtime # last modification timestamp
                    filesize = s.st_size # how large is this file?

                    base, ext = os.path.splitext(entry.name)
                    # use short key names to save space :0
                    data = dict(d=canonical_dirpath, f=entry.name,
                                e=ext, mt=modtime, sz=filesize)

                    # do a crude approximation by reading only the first N bytes
                    if take_checksum:
                        fullpath = os.path.join(dirpath, entry.name)
                        with open(fullpath, 'rb') as f:
                            first_N_bytes = f.read(N_BYTES_FOR_CHECKSUM)
                            data['crc32'] = binascii.crc32(first_N_bytes)

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
    parser.add_argument("--checksum", help="take a crc32 checksum of first N bytes of files (SLOW!)",
                        action="store_true")

    args = parser.parse_args()
    create_inventory(args.root, args.label, args.checksum)
