from __future__ import print_function, unicode_literals, division, absolute_import
from abc import ABCMeta, abstractmethod
import logging
import sys
import os

if sys.version_info[0] < 3:
    import cookielib
else:
    import http.cookiejar as cookielib

try:
    import requests
except ImportError:
    logging.critical('You must install "requests" for this script to work.  Try "pip install requests".')
    sys.exit(1)

import metadata
import config


class BaseTracker(object):
    """
    Base class for representing a private tracker.
    """

    __metaclass__ = ABCMeta

    # The file extensions allowed by the tracker
    # NOTE: to allow all file types, set this to None
    FILE_EXTENSION_WHITELIST = {
        '.mkv',
        '.mp4',
        '.avi',
        '.ts',
        '.nfo',
        '.png',
        '.sub',
        '.idx',
        '.srt',
    }

    # The video containers allowed by the tracker
    CONTAINER_WHITELIST = {
        metadata.Containers.MKV,
        metadata.Containers.MP4,
        metadata.Containers.AVI,
    }

    # The container strings expected by the tracker's upload form
    CONTAINER_STRING = {
        metadata.Containers.MKV: 'MKV',
        metadata.Containers.MP4: 'MP4',
        metadata.Containers.AVI: 'AVI',
    }

    # The source strings expected by the tracker's upload form
    SOURCE_STRING = {
        metadata.Sources.BLURAY: 'Blu-ray',
        metadata.Sources.HDDVD: 'HD-DVD',
        metadata.Sources.DVD: 'DVD',
        metadata.Sources.HDTV: 'HDTV',
        metadata.Sources.WEBDL: 'WEB-DL',
        metadata.Sources.CAM: 'CAM (TS)',
        metadata.Sources.SCREENER: 'Screener',
        metadata.Sources.R5: 'R5',
        metadata.Sources.OTHER: 'Other',
    }

    # The codec strings expected by the tracker's upload form
    CODEC_STRING = {
        metadata.Codecs.X264: 'x264',
        metadata.Codecs.XVID: 'XviD',
        metadata.Codecs.DIVX: 'DivX',
        metadata.Codecs.H264: 'h.264',
        metadata.Codecs.DVDR: 'DVDR',
        metadata.Codecs.MPEG2: 'MPEG-2',
        metadata.Codecs.AVC: 'AVC',
        metadata.Codecs.VC1: 'VC-1',
    }

    # The set of release groups specifically banned at the tracker
    BANNED_GROUPS = set()

    def __init__(self):

        cookie_file = os.path.join(config.COOKIE_DIR, '.{tracker}.cookies'.format(tracker=self))

        self.session = requests.Session()
        self.session.cookies = cookielib.LWPCookieJar(filename=cookie_file)
        self.base_url = None
        self.announce_url = None

        # Attempt to load cookies if we already have them
        try:
            self.session.cookies.load()
        except IOError:
            pass

    def __repr__(self):
        return self.__class__.__name__

    def request(self, path='', method='GET', params=None, data=None, files=None, verify=None, allow_redirects=True):
        url = self.base_url + path
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                files=files,
                verify=verify,
                allow_redirects=allow_redirects,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            msg = 'Could not connect to {site}: {error}'
            raise TrackerError(msg.format(site=self, error=e))
        return response

    def check_upload(self, upload):
        """
        Check to make sure the upload conforms to the tracker's standards.
        """

        # Make sure everything is in order
        assert upload.metadata_is_verified
        assert upload.technical_is_verified
        assert upload.mediainfo is not None
        assert upload.torrent is not None
        assert upload.bbcode is not None
        assert upload.title is not None
        assert upload.film_description is not None
        assert upload.source is not None
        assert upload.codec is not None
        assert upload.container is not None
        assert upload.resolution is not None
        assert (upload.screenshots is not None) or (upload.take_screens is False)

        # Check container
        if upload.release.container not in self.CONTAINER_WHITELIST:
            msg = 'The {container} container is not allowed at {tracker}'
            raise TrackerError(msg.format(container=upload.release.container, tracker=self))

        # Check release group
        if upload.release.group in self.BANNED_GROUPS:
            msg = 'The release group "{group}" is not allowed at {tracker}'
            raise TrackerError(msg.format(group=upload.release.group, tracker=self))

    @abstractmethod
    def take_upload(self, upload, dry_run=False):
        """
        Upload a release to the tracker.

        NOTE: Subclasses must override this method!
        """
        raise NotImplementedError

    def get_torrent_group(self, imdb_object):
        """
        Ask the tracker for the group ID for this film.
        """
        return None

    def dupe_check(self, release):
        """
        Ask the tracker for any similar releases that already exist.
        """
        return []


class TrackerError(Exception):
    pass