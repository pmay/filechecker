import argparse
import hashlib
import os
import sys

from os.path import isdir, join, relpath
from filechecker import __version__

default_manifest = "manifest.md5"
cs_ignore = [".md5", ".sha256"]

def md5sum(filename, blocksize=256*128):
    hash = hashlib.md5()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            hash.update(block)
    return hash.hexdigest()


def checksum_dir(directory, recursive=False, ignore_ext=cs_ignore):
    """Checksums the specified directory, recursing down into subfolders as necessary"""
    if isdir(directory):
        for root, dirs, files in os.walk(directory):
            files = [file for file in files if not file.lower().endswith(tuple(ignore_ext))]

            for file in files:
                path = join(root, file)
                r_path = join(".",relpath(path, directory))
                hash = md5sum(path)
                #yield "{0} *{1}\n".format(hash, r_path)
                yield (hash, r_path)
            if not recursive:
                # all done
                return


def calculate_checksums(directory, recursive=False, manifest_file=None):
    if manifest_file is None:
        manifest_file = join(directory, default_manifest)

    with open(manifest_file, 'w') as manifest:
        for cs in checksum_dir(directory, recursive):
            manifest.write("{0} *{1}\n".format(cs[0], cs[1]))
            manifest.flush()


def _list_files(directory, base_path=None, recursive=True):
    """ Lists the files within the specified directory relative to the base_path
    :param path: the top level path to start listing from
    :param recursive: true if listing should include sub-directories
    :return: a list of files in the specified directory and sub-folders as necessary
    """
    files = []
    if base_path is None:
        base_path = directory
    try:
        for p in os.scandir(directory):
            if p.is_file():
                files.append(join(".", relpath(p.path, base_path)))
            if recursive and p.is_dir():
                files.extend(_list_files(p.path, base_path, recursive))
    except (IOError, OSError) as e:
        print ("Permission Error ({0}): {1} for {2}".format(e.errno, e.strerror, directory))

    return files


def validate_checksums(directory, manifest_file=None):
    if manifest_file is None:
        manifest_file = join(directory, default_manifest)

    # Load checksums from target manifest
    original_cs = {}
    with open(manifest_file, 'r') as manifest:
        for line in manifest:
            line_s = line.split(' ')
            original_cs[line_s[1][1:].strip()] = line_s[0]

    # now list all files in the directory (incl. sub folders)
    dir_filenames = {fname: None for fname in _list_files(directory)}

    results = {"found": {"correct": [], "incorrect": []},
               "missing": []}

    for f in original_cs.keys():
        full_path = join(directory, f)
        if os.path.exists(full_path):
            current_cs = md5sum(full_path)
            if current_cs == original_cs[f]:
                results["found"]["correct"].append(f)
            else:
                results["found"]["incorrect"].append(f)
            del dir_filenames[f]
        else:
            results["missing"].append(f)

    # list all original
    if len(results["found"]["correct"]) == len(original_cs):
        print ("All files in manifest correct")

    else:
        print ("Correct Files:")
        print (results["found"]["correct"])

        print ("\nIncorrect Files:")
        print (results["found"]["incorrect"])

    if len(results["missing"]) > 0:
        print ("\nFiles listed in manifest, not in directory:")
        print (results["missing"])

    if len(dir_filenames) > 0:
        print ("\nFiles not listed in manifest:")
        print (dir_filenames.keys())


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    # Process CLI arguments #
    ap = argparse.ArgumentParser(prog="filechecker",
                                 description="Checksum creator/validator")

    actionparser = ap.add_subparsers(title='Actions', dest='actions')

    ## Args for creating manifests
    create_parser = actionparser.add_parser("create")
    create_parser.add_argument("-m", dest="manifest", help="the manifest to create [default: manifest.md5 in dir]")
    create_parser.add_argument("-r", "--recursive", dest="recursive", action="store_true",
                               help="recurse into sub-folders [defaults")
    create_parser.set_defaults(func=calculate_checksums)

    ## Args for validating manifests
    validate_parser = actionparser.add_parser("validate")
    validate_parser.add_argument("-m", dest="manifest", help="the manifest to validate [default: manifest.md5 in dir]")
    validate_parser.set_defaults(func=validate_checksums)

    ## Common args
    ap.add_argument("dir", help="Directory of files to process")

    ap.add_argument("-v", "--version", action="version", version='%(prog)s v' + __version__,
                    help="display program version")
    args = ap.parse_args()

    try:
        #calculate_checksums(args.dir, args.recursive, args.out)
        if args.actions=='create':
            calculate_checksums(args.dir, args.recursive, args.manifest)
        elif args.actions=='validate':
            validate_checksums(args.dir, args.manifest)
    except AttributeError:
        ap.print_help()


if __name__=='__main__':
    main()