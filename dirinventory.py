# created: 2018-12-01

import os
import sys
from collections import Counter

basename_counter = Counter()
extension_counter = Counter()

# run with python >= 3.5 to get os.walk to use the MUCH faster os.scandir function
assert float(sys.version[:3]) >= 3.5

# which directories NOT to recurse into
# .ptvs is python tools for visual studio
IGNORE_DIRS = ('.git', '.ptvs', 'node_modules')

rootdir = sys.argv[1]
assert os.path.isdir(rootdir)

for dirpath, dirnames, filenames in os.walk(rootdir, topdown=True):
    # canonicalize dirpath relative to rootdir
    assert dirpath.startswith(rootdir)
    canonical_dirpath = dirpath[len(rootdir):]
    if canonical_dirpath and canonical_dirpath[0] == '/':
        canonical_dirpath = canonical_dirpath[1:]
        assert canonical_dirpath[0] != '/'

    for f in filenames:
        base, ext = os.path.splitext(f)
        basename_counter[base] += 1
        extension_counter[ext] += 1

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

print(extension_counter.most_common(100))
