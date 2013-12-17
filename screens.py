#!/usr/bin/env python

"""
Takes screenshots of a set of video files, and uploads them to an image host.
"""

from __future__ import print_function, unicode_literals, division, absolute_import
import logging
import argparse
import os

import files
import image_hosts
import config

image_host = image_hosts.ImageBam

config.set_log_file_name(False)

# Set up the argument parser
parser = argparse.ArgumentParser(description='Takes screenshots of one or more video files, '
                                             'and uploads them to an image host.')
parser.add_argument(
    'file_list',
    type=str,
    metavar='video-file',
    nargs='+',
    help='file or directory containing the release'
)
parser.add_argument(
    '-n',
    '--num-screenshots',
    type=int,
    metavar='<number>',
    dest='num_screenshots',
    default=config.NUM_SCREENSHOTS,
    help='number of screenshots to save and upload'
)
parser.add_argument(
    '-U',
    '--no-upload',
    dest='upload',
    default=True,
    action='store_false',
    help='do not upload; save screenshots and exit'
)
args = parser.parse_args()


for path in args.file_list:

    logging.info('------------------------------------------------------------')
    logging.info(os.path.basename(path))
    logging.info('------------------------------------------------------------')

    try:

        screenshots = files.Screenshots(path)
        screenshots.take(args.num_screenshots)
        if args.upload:
            screenshots.upload(
                image_host=image_host,
                delete_after_upload=config.DELETE_SCREENS_AFTER_UPLOAD,
            )
            logging.info('BBCode:\n' + screenshots.bbcode)
        else:
            for screenshot_path in screenshots.files:
                logging.info(screenshot_path)

    except (files.ScreenshotsError, image_hosts.ImageHostError) as e:

        logging.error(e)
        continue

    except Exception:

        logging.exception('An unexpected error occurred. Please report the following information to the developers:')
        continue