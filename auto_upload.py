#!/usr/bin/env python

"""
Auto uploads film releases to a BitTorrent tracker.

Built for TehConnection.eu, but easily extensible for other trackers.

Compatible with Python 2.7, 3.2, and 3.3.
"""

from __future__ import print_function, unicode_literals, division, absolute_import
import argparse
import logging
import sys
import os

import trackers
import uploads
import config
import files


# Snippet from the `six` library to help with Python3 compatibility
if sys.version_info[0] == 3:
    text_type = str
else:
    text_type = unicode


tracker = trackers.TehConnection

# Set up the argument parser
parser = argparse.ArgumentParser(description='Auto uploads film releases to a BitTorrent tracker.')
parser.add_argument(
    'file_list',
    type=text_type,
    metavar='release-path',
    nargs='+',
    help='file or directory containing the release',
)
parser.add_argument(
    '--imdb',
    default=None,
    help='manually specify the IMDb ID or URL for the release(s) you are uploading',
)
parser.add_argument(
    '--dry-run',
    dest='dry_run',
    action='store_true',
    default=False,
    help='do a dry run -- everything except posting the upload form to the tracker',
)
parser.add_argument(
    '--no-screens',
    dest='take_screens',
    action='store_false',
    help='do not take screenshots',
)
parser.add_argument(
    '-n',
    '--num-screenshots',
    type=int,
    metavar='<number>',
    dest='num_screenshots',
    default=config.NUM_SCREENSHOTS,
    help='number of screenshots to save and upload',
)
parser.add_argument(
    '-d',
    '--delete-unwanted-files',
    dest='delete_unwanted_files',
    action='store_true',
    default=config.DELETE_UNWANTED_FILES,
    help='delete files that are not whitelisted by the tracker (such as .rar files)',
)
args = parser.parse_args()


# Every argument to this script is treated as a path to a release to be uploaded
release_list = files.get_paths(args.file_list)

if len(release_list) == 0:
    logging.critical('You must give this script at least one file or directory to process!')
    sys.exit(1)

for path in release_list:

    # Log exceptions but don't raise them; just continue

    try:

        files.set_log_file_name(os.path.basename(path) + '.log')
        upload = uploads.Upload(
            path=path,
            tracker=tracker,
            imdb_link=args.imdb,
            take_screenshots=args.take_screens,
            num_screenshots=args.num_screenshots,
            delete_unwanted_files=args.delete_unwanted_files,
        )

        logging.info('------------------------------------------------------------')
        logging.info(upload.release.name)
        logging.info('------------------------------------------------------------')

        upload.start(
            dry_run=args.dry_run,
        )

    except uploads.UploadInterruptedError as e:

        logging.error(e)
        continue

    except Exception:

        logging.exception('An unexpected error occurred. Please report the following information to the developers:')
        continue
