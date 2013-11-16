#!/usr/bin/env python

"""
Auto uploads film releases to a BitTorrent tracker.

Built for TehConnection.eu, but easily extensible for other trackers.

Compatible with Python 2.7, 3.2, and 3.3.
"""

from __future__ import print_function, unicode_literals, division, absolute_import
import sys
import os
import logging

import __init__
import config
import files
import trackers
import uploads

config.set_log_file_name('macguffin.log')

# Every argument to this script is treated as a path to a release to be uploaded
release_list = files.get_paths(sys.argv[1:])

if len(release_list) == 0:
    logging.critical('You must give this script at least one file or directory to process!')
    sys.exit(1)

for path in release_list:

    # Log exceptions but don't raise them; just continue
    try:

        config.set_log_file_name(os.path.split(path)[1] + '.log')
        upload = uploads.Upload(path=path, tracker=trackers.TehConnection)
        logging.info('------------------------------------------------------------')
        logging.info(upload.release.name)
        logging.info('------------------------------------------------------------')
        upload.start()

    except uploads.UploadInterruptedError as e:

        logging.error(e)
        continue

    except Exception:

        logging.exception('An unexpected error occurred. Please report the following information to the developers:')
        continue