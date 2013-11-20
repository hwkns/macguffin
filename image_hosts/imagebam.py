from __future__ import print_function, unicode_literals, division, absolute_import
import re
import io
import os
import sys
import logging

try:
    from bs4 import BeautifulSoup
except ImportError:
    logging.critical('You must install "beautifulsoup4" for this script to work.  Try "pip install beautifulsoup4".')
    sys.exit(1)

import config
from .image_host import BaseImageHost, ImageHostError


class ImageBam(BaseImageHost):

    def __init__(self):

        super(ImageBam, self).__init__()

        if not (config.IMGBAM_USERNAME and config.IMGBAM_PASSWORD):
            raise ImageHostError('You must specify your ImageBam username and password in config.py')

        self.thumbnail_size = '350'
        self.thumb_file_type = 'jpg'
        self.gallery_options = '1'

    def __repr__(self):
        return 'ImageBam.com'

    def login(self):

        url = 'http://www.imagebam.com/login'
        data = {
            'action': 'true',
            'nick': config.IMGBAM_USERNAME,
            'pw': config.IMGBAM_PASSWORD
        }
        response = self.session.post(url, data=data)
        response.raise_for_status()

        # If we didn't get redirected, something went wrong
        if not response.history:
            soup = BeautifulSoup(response.text)
            error_message = soup.find('div', class_='box_error')
            if error_message:
                logging.error(error_message.string.strip())
            raise ImageHostError('{site} login failed!'.format(site=self))

    def upload(self, image_paths):

        if not image_paths:
            raise ImageHostError('No files to upload!')

        for image in image_paths:
            if (not os.path.isfile(image)) or (not image.endswith('.png')):
                msg = 'The file "{file}" does not exist or is not a PNG image.'
                raise ImageHostError(msg.format(file=image))

        self.login()

        # Upload files
        url = 'http://www.imagebam.com/sys/upload/save'
        data = {
            'content_type': '0',
            'thumb_size': self.thumbnail_size,
            'thumb_aspect_ratio': 'resize',
            'thumb_file_type': self.thumb_file_type,
            'gallery_options': self.gallery_options,
            'gallery_title': '',
            'gallery_description': ''
        }
        files = []
        file_objects = []
        for n in range(len(image_paths)):
            img_num = str(n + 1).zfill(3)
            file_objects.append(io.open(image_paths[n], mode='rb'))
            files.append((
                'file[]',
                (
                    'image{number}.png'.format(number=img_num),
                    file_objects[n]
                )
            ))

        logging.info('Uploading screenshots to ImageBam...')
        response = self.session.post(url, data=data, files=files)
        response.raise_for_status()
        logging.info('Screenshot upload completed: http://www.imagebam.com/gallery-organizer')

        for file_obj in file_objects:
            file_obj.close()

        self._html = response.text

        table_regex = re.compile(r'(<table style=\'width:100%;\'>)((.|\s)*?)(</table>)')
        table_html = ''.join(table_regex.findall(self._html)[0])
        bbcode_regex = re.compile(r'\[URL=.*?\[/URL]')
        self.bbcode_links = bbcode_regex.findall(table_html)
        link_regex = re.compile(r'\<a href=.*?></a>')
        self.html_links = link_regex.findall(table_html)
        url_regex = re.compile(r'http://www.imagebam.com/.*?[a-z0-9]{12,18}(?=")')
        self.urls = url_regex.findall(''.join(self.html_links))

        return True