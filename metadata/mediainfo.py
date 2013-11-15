from __future__ import print_function, unicode_literals, division, absolute_import
import re
import os
import logging
import subprocess
from io import StringIO

from .utils import Containers, Codecs
import config


class Mediainfo(object):
    """
    Represents the key/value pairs output by the mediainfo command.

    A Mediainfo object can be treated like a dictionary.  For example,
    to get the duration of the video stream:

    m = Mediainfo('/path/to/video_file.mkv')
    d = m['Video']['Duration']

    This code will generate a KeyError if there is no 'Video' section in
    the mediainfo output, or if 'Duration' is not present in that section.
    """

    def __init__(self, path=None, base_path=None, text=None):

        if path:
            self.path = os.path.abspath(os.path.expanduser(path))
            assert os.path.isfile(self.path)

            if base_path:
                base_path = os.path.abspath(os.path.expanduser(base_path))
                assert os.path.isdir(base_path)

                # First, cd to the base path; then we'll run mediainfo using the relative path
                command = 'cd "{dir}"; '.format(dir=base_path)
                relative_path = path.replace(base_path, '').lstrip('/')

            else:
                command = ''
                relative_path = self.path

            # Run mediainfo on the path and store the result in self.text
            command += '"{mediainfo}" "{file}"'
            command = command.format(mediainfo=config.MEDIAINFO_PATH, file=relative_path)
            try:
                output = subprocess.check_output(command, shell=True).strip()
            except subprocess.CalledProcessError as e:
                output = e.output.decode(encoding='utf-8')
                raise MediainfoError('Could not get mediainfo output: {output}'.format(output=output))
            else:
                self.text = output.decode(encoding='utf-8')

        elif text:
            self.text = text.strip()

        else:
            raise MediainfoError('No file path or text provided.')

        self.contents = dict()
        self.encoding_settings = dict()
        self.container = None
        self.codec = None
        self.width = None
        self.height = None
        self.unique_id = None
        self.has_chapters = False

    def __getitem__(self, item):
        return self.contents[item]

    def __setitem__(self, key, value):
        self.contents[key] = value

    def get(self, key, default=None):
        return self.contents.get(key, default)

    def parse(self):
        section = 'General'
        self[section] = dict()

        for line in StringIO(self.text):
            line = line.strip()

            if not line:
                pass

            if ':' not in line:
                section = line
                self[section] = dict()

            else:
                try:
                    partitioned = line.partition(':')
                    key = partitioned[0].strip()
                    value = partitioned[2].strip()
                    self[section][key] = value
                except AttributeError:
                    msg = 'Could not parse line "{text}"'
                    logging.error(msg.format(text=line))

        logging.debug('Parsed mediainfo output.')

    def get_info(self):

        # Does it have chapters?
        if self.get('Menu') and self['Menu'].keys():
            self.has_chapters = True

        # Get container
        try:
            container = self['General']['Format']
            self.container = CONTAINERS.get(container.lower())
            logging.debug('Container: ' + container)
        except KeyError:
            msg = 'Unable to parse container from mediainfo.\n{text}'
            raise MediainfoError(msg.format(text=self.text))

        # Get codec
        try:
            codec = self['Video']['Writing library']
            if codec.lower().startswith('x264'):
                self.codec = Codecs.X264
            elif codec.lower().startswith('xvid'):
                self.codec = Codecs.XVID
            else:
                msg = 'Did not recognize codec: {codec}'
                raise MediainfoError(msg.format(codec=codec))
        except KeyError:
            # A hack to take care of H.264 that wasn't encoded with x264
            # TODO: better handling of H.264; in particular, we might hit another KeyError here
            video_format = self['Video']['Format']
            if video_format == 'AVC':
                self.codec = Codecs.H264
            else:
                msg = 'Unable to parse codec from mediainfo.\n{text}'
                raise MediainfoError(msg.format(text=self.text))

        # Get width and height
        try:
            self.width = int(re.sub(r'\D', '', self['Video']['Width']))
            self.height = int(re.sub(r'\D', '', self['Video']['Height']))
        except KeyError:
            msg = 'Unable to parse width/height from mediainfo.\n{text}'
            raise MediainfoError(msg.format(text=self.text))
        else:
            msg = 'Resolution: {w} x {h}'
            logging.info(msg.format(w=self.width, h=self.height))

        # Get encoding settings
        if self.codec == Codecs.X264:
            try:
                encoding_settings = self['Video']['Encoding settings'].split(' / ')
                for setting in encoding_settings:
                    (key, delimiter, value) = setting.partition('=')
                    self.encoding_settings[key] = value
            except (KeyError, ValueError):
                msg = 'Unable to parse encoding settings from mediainfo.\n{text}'
                logging.debug(msg.format(text=self.text))


class MediainfoError(Exception):
    pass


# This dict maps lowercase container strings from mediainfo to their Containers enum value
CONTAINERS = {
    'matroska': Containers.MKV,
    'avi': Containers.AVI,
    'mp4': Containers.MP4,
}