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


# Set up the argument parser
parser = argparse.ArgumentParser(description='Auto uploads film releases to a BitTorrent tracker.')
parser.add_argument(
    'file_list',
    type=str,
    metavar='video-file',
    nargs='+',
    help='file or directory containing the release'
)
parser.add_argument(
    '--no-upload',
    dest='dry_run',
    action='store_true',
    help='do a dry run -- everything except posting the upload form to the tracker'
)
parser.add_argument(
    '--no-screens',
    dest='take_screens',
    action='store_false',
    help='do not take screenshots',
)
parser.add_argument(
    '-n',
    type=int,
    metavar='<number>',
    default=config.NUM_SCREENSHOTS,
    help='number of screenshots to save and upload'
)
args = parser.parse_args()


# Every argument to this script is treated as a path to a release to be uploaded
release_list = files.get_paths(args.file_list)

if len(release_list) == 0:
    logging.critical('You must give this script at least one file or directory to process!')
    sys.exit(1)

tracker = trackers.TehConnection

for path in release_list:

    # Log exceptions but don't raise them; just continue
    try:

        config.set_log_file_name(os.path.basename(path) + '.log')
        upload = uploads.Upload(path=path, tracker=tracker, screens=args.take_screens)
        logging.info('------------------------------------------------------------')
        logging.info(upload.release.name)
        logging.info('------------------------------------------------------------')
        upload.start(dry_run=args.dry_run)

    except uploads.UploadInterruptedError as e:

        logging.error(e)
        continue

    except Exception:

        logging.exception('An unexpected error occurred. Please report the following information to the developers:')
        continue