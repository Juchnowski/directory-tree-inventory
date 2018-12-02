# created: 2018-12-01
# input: argv[1] is the root directory name to start the inventory
#        argv[2] is your computer's name (or whatever you want to put in here!)
# outputs a .jsonl string containing a json line for each file's metadata
# (the first line represents JSON metadata)

# goal: be FAST!!!

import json
import os
import sys
import time
from collections import Counter

# run with python >= 3.5 to get os.walk to use the MUCH faster os.scandir function
assert float(sys.version[:3]) >= 3.5

# which directories NOT to recurse into
# (.ptvs is python tools for visual studio)
#IGNORE_DIRS = ('.git', '.ptvs', 'node_modules')
IGNORE_DIRS = ()

rootdir = sys.argv[1]
assert os.path.isdir(rootdir)

machine_name = sys.argv[2]

# first line metadata
metadata = dict(ts=time.time(), IGNORE_DIRS=IGNORE_DIRS, machine=machine_name, rootdir=os.path.abspath(rootdir))
print(json.dumps(metadata))

basename_counter = Counter()
extension_counter = Counter()
dirnames_counter = Counter()

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
                data = dict(d=canonical_dirpath, f=entry.name, e=ext, mt=modtime, sz=filesize)
                print(json.dumps(data))

    # from https://docs.python.org/3/library/os.html#os.walk
    # When topdown is True, the caller can modify the dirnames list
    # in-place (perhaps using del or slice assignment), and walk() will
    # only recurse into the subdirectories whose names remain in dirnames;
    # this can be used to prune the search
    for d in IGNORE_DIRS:
        try:
            dirnames.remove(d)
        except ValueError:
            pass

#print(dirnames_counter.most_common(100))
#print()
#print(basename_counter.most_common(100))
#print()
#print(extension_counter.most_common(100))
