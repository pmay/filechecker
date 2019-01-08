import argparse
import hashlib
import os
import sys

from os.path import isdir, join, relpath
from progressbar import ProgressBar, UnknownLength
from filechecker import __version__

default_alg = "sha256"
default_manifest_prefix = "manifest."
#cs_ignore = [".md5", ".sha256"]
cs_ignore = ["."+x for x in hashlib.algorithms_guaranteed]

def hash_data(filename, algorithm=default_alg, blocksize=256*128):
    hash = hashlib.new(algorithm)
    with open(u'\\\\?\\'+filename, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            hash.update(block)
    return hash.hexdigest()


def checksum_dir(directory, recursive=False, algorithm=default_alg, formats=None):
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
                r_path = join(".", relpath(path, directory))
                hash = hash_data(path, algorithm)
                #yield "{0} *{1}\n".format(hash, r_path)
                yield (hash, r_path)
            if not recursive:
                # all done
                return


def calculate_checksums(directory, algorithm=default_alg, manifest_file=None, formats=None, recursive=False, timing=True):

    if timing:
        numfiles = _count_files(directory, recursive)
        bar = ProgressBar(max_value=numfiles)

    if manifest_file is None:
        manifest_file = join(directory, default_manifest_prefix+algorithm)

    with open(manifest_file, 'w') as manifest:
        for cs in checksum_dir(directory, recursive, algorithm, formats):
            manifest.write("{0} *{1}\n".format(cs[0], cs[1]))
            manifest.flush()
            if timing:
                bar.update(bar.value+1)

    if timing:
        bar.finish()


def _count_files(path, recursive=True):
    """ Counts the number of files within the specified directory
    :param path: the top level path to count files in
    :param recursive: true if counting should include sub-directories
    :return: the number of files in the specified path
    """
    count = 0
    try:
        for p in os.scandir(path):
            if p.is_file():
                count += 1
            if recursive and p.is_dir():
                count += _count_files(p.path, recursive)
    except (IOError, OSError) as e:
        print("Permission Error ({0}): {1} for {2}".format(e.errno, e.strerror, path))

    return count


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
        print("Permission Error ({0}): {1} for {2}".format(e.errno, e.strerror, directory))

    return files


def _print_results_list(results_list):
    print('\n'.join(results_list))


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


def validate_checksums(directory, algorithm=None, manifest_file=None, timing=True):
    # algorithm overides algorithm calculated from manifest file name

    if manifest_file is None:
        manifest_file = join(directory, default_manifest_prefix+default_alg)

    # set algorithm based on manifest extension
    manifest_alg = algorithm

    if manifest_alg is None:
        manifest_alg = manifest_file.rsplit('.', 1)[1]


    # TODO: Improve manifest selection based on length of hash values within the manifest

    # Load checksums from target manifest
    original_cs = {}
    with open(manifest_file, 'r') as manifest:
        for line in manifest:
            line_s = line.rstrip('\r\n').split(' ', 1)
            original_cs[line_s[1][1:].strip()] = line_s[0]

    results = {"found": {"correct": [], "incorrect": []},
               "missing": [],
               "additional": {fname: None for fname in _list_files(directory)}}

    if timing:
        numfiles = len(original_cs.keys())
        bar = ProgressBar(max_value=numfiles)

    for f in original_cs.keys():
        full_path = join(directory, f[2:])
        if os.path.exists(full_path):
            current_cs = hash_data(full_path, algorithm=manifest_alg)
            if current_cs == original_cs[f]:
                results["found"]["correct"].append(f)
            else:
                results["found"]["incorrect"].append(f)
            del results["additional"][f]
        else:
            results["missing"].append(f)

        if timing:
            bar.update(bar.value + 1)

    if timing:
        bar.finish()

    # list all original
    if len(results["found"]["correct"]) == len(original_cs):
        print("All files in manifest correct")

    else:
        print("Correct Files:")
        _print_results_list(results["found"]["correct"])

        print("\nIncorrect Files:")
        _print_results_list(results["found"]["incorrect"])

    if len(results["missing"]) > 0:
        print("\nFiles listed in manifest, not in directory:")
        _print_results_list(results["missing"])

    if len(results["additional"]) > 0:
        print("\nAdditional Files not listed in manifest:")
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
    create_parser.add_argument("-a", "--algorithm", dest="algorithm",
                               choices=hashlib.algorithms_guaranteed,
                               default=default_alg,
                               help="the checksum algorithm to use [default: sha256]")
    create_parser.add_argument("--formats", dest="formats", nargs="+", help="list of file extensions to include (only)")
    #create_parser.add_argument("--ignore", dest="ignore", help="list of additional file extensions to ignore")
    create_parser.add_argument("-m", dest="manifest", help="the manifest to create [default: manifest.md5 in dir]")
    create_parser.add_argument("-r", "--recursive", dest="recursive", action="store_true",
                               help="recurse into sub-folders [default: false]")
    create_parser.add_argument("--no-timing", dest="timing", action="store_false", help="turn off progress bar")
    create_parser.set_defaults(func=calculate_checksums)

    ## Args for validating manifests
    validate_parser = actionparser.add_parser("validate")
    validate_parser.add_argument("-a", "--algorithm", dest="algorithm",
                               choices=hashlib.algorithms_guaranteed,
                               default=default_alg,
                               help="the checksum algorithm to use [default: sha256]")
    validate_parser.add_argument("-m", dest="manifest", help="the manifest to validate [default: manifest.md5 in dir]")
    validate_parser.set_defaults(func=validate_checksums)

    ## Common args
    ap.add_argument("dir", help="Directory of files to process")

    ap.add_argument("-v", "--version", action="version", version='%(prog)s v' + __version__,
                    help="display program version")
    args = ap.parse_args()

    try:
        if args.actions=='create':
            calculate_checksums(args.dir, args.algorithm, args.manifest, args.formats, args.recursive)
        elif args.actions=='validate':
            validate_checksums(args.dir, args.algorithm, args.manifest)
    except AttributeError:
        ap.print_help()


if __name__ == '__main__':
    main()
