from __future__ import print_function, unicode_literals, division, absolute_import
import os
import io
import codecs

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
        self.codec = 'cp437'

        # Assume CP-437 encoding and read in the file
        with io.open(self.path, mode='rb') as nfo_file:
            nfo_bytes = nfo_file.read()

        for (bom, codec) in byte_order_mark_codecs.items():
            if nfo_bytes.startswith(bom):
                self.codec = codec
                break

        try:
            self.text = nfo_bytes.decode(encoding=self.codec)
        except UnicodeDecodeError:
            msg = 'Could not decode NFO file with codec {codec}'
            raise NFOError(msg.format(codec=self.codec))

        # Generate BBCode
        self.bbcode += '[spoiler=NFO][size=2][pre]'
        self.bbcode += self.text
        self.bbcode += '[/pre][/size][/spoiler]\n'


class NFOError(Exception):
    pass