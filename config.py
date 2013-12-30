from __future__ import print_function, unicode_literals, division, absolute_import
import os
import sys
import logging


####################################################
##  Edit this section with your account details.  ##
####################################################

TC_USERNAME = ''
TC_PASSWORD = ''
TC_PASSKEY = ''

TMDB_API_KEY = ''

IMGBAM_USERNAME = ''
IMGBAM_PASSWORD = ''

###################################################
##  Edit this section with your system details.  ##
###################################################

# Set this to your rtorrent watch folder path to automatically seed new torrents
WATCH_DIR = '~'

# Logs will be written to this directory, as {Release.Name}.log
# NOTE: Existing logs will be overwritten.
LOG_DIR = '~'

# All tracker cookies will be saved here
COOKIE_DIR = '~'

# Paths to various binaries on your system (in case they are not on the system path)
MEDIAINFO_PATH = 'mediainfo'
FFMPEG_PATH = 'ffmpeg'
FFPROBE_PATH = 'ffprobe'
UNRAR_PATH = 'unrar'

# Set this to True if you want to delete files that don't make it into the uploaded torrent.
# NOTE: If you want to cross-seed, this might not be a good idea.
DELETE_UNWANTED_FILES = False

# How many screenshots to upload by default
NUM_SCREENSHOTS = 4
DELETE_SCREENS_AFTER_UPLOAD = True

##################################################################
##  End user-edited section                                     ##
##################################################################

# Expand paths
if WATCH_DIR is not None:
    WATCH_DIR = os.path.expanduser(WATCH_DIR)
if LOG_DIR is not None:
    LOG_DIR = os.path.expanduser(LOG_DIR)
if COOKIE_DIR is not None:
    COOKIE_DIR = os.path.expanduser(COOKIE_DIR)

# Set logging level for the requests lib to warning+
requests_log = logging.getLogger('requests')
requests_log.setLevel(logging.WARNING)


def set_log_file_name(file_name):
    """
    Set the file name for log output.
    """

    # Remove all logging handlers from the root logger
    logger = logging.getLogger('')
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.flush()
        handler.close()

    # Configure console logging
    console_log_format = logging.Formatter('%(module)-15s: %(levelname)-8s %(message)s')
    console_log_handler = logging.StreamHandler(sys.stdout)
    console_log_handler.setFormatter(console_log_format)
    console_log_handler.setLevel(logging.INFO)
    logger.addHandler(console_log_handler)

    # Configure disk logging
    if file_name:
        log_path = os.path.join(LOG_DIR, file_name)
        disk_log_format = logging.Formatter('%(asctime)s %(module)-15s: %(levelname)-8s %(message)s')
        disk_log_handler = logging.FileHandler(filename=log_path, mode='w', encoding='utf-8')
        disk_log_handler.setFormatter(disk_log_format)
        disk_log_handler.setLevel(logging.DEBUG)
        logger.addHandler(disk_log_handler)

    logger.setLevel(logging.DEBUG)