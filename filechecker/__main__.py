import argparse
import hashlib
import os
import sys

from os.path import isdir, join, relpath
from filechecker import __version__


def md5sum(filename, blocksize=256*128):
    hash = hashlib.md5()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            hash.update(block)
    return hash.hexdigest()


def checksum_dir(directory, recursive=False):
    """Checksums the specified directory, recursing down into subfolders as necessary"""
    if isdir(directory):
        for root, dirs, files in os.walk(directory):
            for file in files:
                path = join(root, file)
                r_path = join(".",relpath(path, directory))
                hash = md5sum(path)
                yield "{0} *{1}".format(hash, r_path)
            if not recursive:
                # all done
                return


def calculate_checksums(directory, recursive=False):
    for cs in checksum_dir(directory, recursive):
        print(cs)


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    # Process CLI arguments #
    ap = argparse.ArgumentParser(prog="filechecker",
                                 description="Checksum creator/validator")

    ap.add_argument("dir", help="Directory of files to process")
    ap.add_argument("-r", "--recursive", dest="recursive", action="store_true",
                    help="recurse into sub-folders [defaults")
    ap.add_argument("-v", "--version", action="version", version='%(prog)s v' + __version__,
                    help="display program version")
    arguments = ap.parse_args()

    try:
        calculate_checksums(arguments.dir, arguments.recursive)
    except AttributeError:
        ap.print_help()

if __name__=='__main__':
    main()