import argparse
import hashlib
import os
import sys

from os.path import isdir, join, relpath
from filechecker import __version__

default_manifest = "manifest.sha256"
cs_ignore = [".md5", ".sha256"]


def hash_data(filename, algorithm="sha256", blocksize=256*128):
    hash = hashlib.new(algorithm)
    #hash = hashlib.md5()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            hash.update(block)
    return hash.hexdigest()


def checksum_dir(directory, recursive=False, formats=None):
    """Checksums the specified directory, recursing down into subfolders as necessary"""

    ignore_ext = cs_ignore

    if isdir(directory):
        for root, dirs, files in os.walk(directory):
            if formats is None:
                filtered_files = [file for file in files if not file.endswith(tuple(ignore_ext))]
            else:
                filtered_files = [file for file in files if (file.endswith(tuple(formats)) and
                                                             not file.endswith(tuple(ignore_ext)))]

            for file in filtered_files:
                path = join(root, file)
                r_path = join(".",relpath(path, directory))
                hash = hash_data(path)
                #yield "{0} *{1}\n".format(hash, r_path)
                yield (hash, r_path)
            if not recursive:
                # all done
                return


def calculate_checksums(directory, recursive=False, formats=None, manifest_file=None):
    if manifest_file is None:
        manifest_file = join(directory, default_manifest)

    with open(manifest_file, 'w') as manifest:
        for cs in checksum_dir(directory, recursive, formats):
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


def _print_results_list(results_list):
    print ('\n'.join(results_list))


def _write_report(results):
    import csv
    userdir = os.path.expanduser("~")
    res_folder = join(userdir, "filechecker/reports")
    if not os.path.exists(res_folder):
        os.makedirs(res_folder)

    with open(join(res_folder, "correct.csv"), 'w', newline='') as correct_csv:
        out = csv.writer(correct_csv)
        for el in results["found"]["correct"]:
            out.writerow([el])

    with open(join(res_folder, "incorrect.csv"), 'w', newline='') as incorrect_csv:
        out = csv.writer(incorrect_csv)
        for el in results["found"]["incorrect"]:
            out.writerow([el])

    with open(join(res_folder, "missing.csv"), 'w', newline='') as missing_csv:
        out = csv.writer(missing_csv)
        for el in results["missing"]:
            out.writerow([el])

    with open(join(res_folder, "additional.csv"), 'w', newline='') as additional_csv:
        out = csv.writer(additional_csv)
        for el in results["additional"]:
            out.writerow([el])

def validate_checksums(directory, manifest_file=None):
    if manifest_file is None:
        manifest_file = join(directory, default_manifest)

    # Load checksums from target manifest
    original_cs = {}
    with open(manifest_file, 'r') as manifest:
        for line in manifest:
            line_s = line.rstrip('\r\n').split(' ')
            original_cs[line_s[1][1:].strip()] = line_s[0]

    results = {"found": {"correct": [], "incorrect": []},
               "missing": [],
               "additional": {fname: None for fname in _list_files(directory)}}

    for f in original_cs.keys():
        full_path = join(directory, f)
        if os.path.exists(full_path):
            current_cs = hash_data(full_path)
            if current_cs == original_cs[f]:
                results["found"]["correct"].append(f)
            else:
                results["found"]["incorrect"].append(f)
            del results["additional"][f]
        else:
            results["missing"].append(f)

    # list all original
    if len(results["found"]["correct"]) == len(original_cs):
        print ("All files in manifest correct")

    else:
        print ("Correct Files:")
        _print_results_list(results["found"]["correct"])

        print ("\nIncorrect Files:")
        _print_results_list(results["found"]["incorrect"])

    if len(results["missing"]) > 0:
        print ("\nFiles listed in manifest, not in directory:")
        _print_results_list(results["missing"])

    if len(results["additional"]) > 0:
        print ("\nAdditional Files not listed in manifest:")
        _print_results_list(results["additional"])

    _write_report(results)


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    # Process CLI arguments #
    ap = argparse.ArgumentParser(prog="filechecker",
                                 description="Checksum creator/validator")

    actionparser = ap.add_subparsers(title='Actions', dest='actions')

    ## Args for creating manifests
    create_parser = actionparser.add_parser("create")
    create_parser.add_argument("--formats", dest="formats", nargs="+", help="list of file extensions to include (only)")
    #create_parser.add_argument("--ignore", dest="ignore", help="list of additional file extensions to ignore")
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
        if args.actions=='create':
            calculate_checksums(args.dir, args.recursive, args.formats, args.manifest)
        elif args.actions=='validate':
            validate_checksums(args.dir, args.manifest)
    except AttributeError:
        ap.print_help()


if __name__=='__main__':
    main()