from __future__ import print_function, unicode_literals, division, absolute_import
import os
import io
import codecs
import logging

byte_order_mark_codecs = {
    codecs.BOM_UTF8: 'utf-8-sig',
    codecs.BOM_UTF32_LE: 'utf-32le',
    codecs.BOM_UTF32_BE: 'utf-32be',
    codecs.BOM_UTF16_LE: 'utf-16le',
    codecs.BOM_UTF16_BE: 'utf-16be'
}


class NFO(object):

    def __init__(self, path):

        path = os.path.expanduser(path)

        assert os.path.isfile(path)
        self.path = os.path.abspath(path)
        self.bbcode = ''

        # Set default encoding to CP437
        self.codec = 'cp437'

        # Read in the file as bytes
        with io.open(self.path, mode='rb') as nfo_file:
            nfo_bytes = nfo_file.read()

        # Look for a BOM at the beginning of the file
        for (bom, codec) in byte_order_mark_codecs.items():
            if nfo_bytes.startswith(bom):
                msg = 'Found BOM for {codec} in NFO.'
                logging.debug(msg.format(codec=codec))
                self.codec = codec
                break

        # Decode NFO contents
        try:
            self.text = nfo_bytes.decode(encoding=self.codec)
        except UnicodeDecodeError:
            msg = 'Could not decode NFO file with codec {codec}'
            raise NFOError(msg.format(codec=self.codec))


class NFOError(Exception):
    pass