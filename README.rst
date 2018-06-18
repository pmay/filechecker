===========
FileChecker
===========

A utility for calculating and validating checksums with the ability to store the manifest in a separate location

How to use
==========

To create a SHA256 checksum manifest: ``filechecker create [-r] {directory}``
The ``-r`` option recursively checksums all sub-folders and adds them to the manifest.

To validate a SHA256 manifest (stored in the same directory): ``filechecker validate {directory}``