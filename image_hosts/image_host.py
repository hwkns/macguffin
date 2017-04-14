# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, division, absolute_import

from abc import ABCMeta, abstractmethod
import logging
import sys

try:
    import requests
except ImportError:
    logging.critical('You must install "requests" for this script to work.  Try "pip install requests".')
    sys.exit(1)


class BaseImageHost(object):
    """
    Base class for representing an image host.
    """

    __metaclass__ = ABCMeta

    def __init__(self):
        self.session = requests.Session()
        self._html = None
        self.bbcode_links = []
        self.html_links = []
        self.urls = []

    def __repr__(self):
        return self.__class__.__name__

    def request(self, url='', method='GET', params=None, data=None, files=None, verify=True, allow_redirects=True):
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
        except requests.ConnectionError as e:
            msg = 'Could not connect to {site}: {error}'
            raise ImageHostError(msg.format(site=self, error=e))
        return response

    @abstractmethod
    def upload(self, list_of_image_paths):
        """
        Upload a set of image files to the host.

        NOTE: Subclasses must override this method!
        """
        raise NotImplementedError


class ImageHostError(Exception):
    pass
