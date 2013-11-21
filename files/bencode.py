from __future__ import print_function, unicode_literals, division, absolute_import
import sys

if sys.version_info[0] >= 3:
    unicode = str


def _bytes(some_str):
    """
    Convert a string (unicode) into UTF-8 bytes.

    @rtype: bytes
    """
    if isinstance(some_str, bytes):
        return some_str
    else:
        return some_str.encode('utf-8')


def _str(some_bytes):
    """
    Attempt to decode bytes into a unicode string using UTF-8.

    Decoding cannot be guaranteed, so be careful.

    @rtype: unicode
    """
    if isinstance(some_bytes, unicode):
        return some_bytes
    else:
        return some_bytes.decode('utf-8')


def bencode(thing):
    """
    Returns the bencoded version of thing as bytes.

    Allowed object types are:
        - list (list)
        - dictionary (dict)
        - integer (int)
        - string (str)
        - bytes object (bytes)

    @rtype: bytes
    """
    if isinstance(thing, int):
        return _bytes('i{thing}e'.format(thing=thing))

    elif isinstance(thing, unicode):
        result = _bytes(unicode(len(_bytes(thing))) + ':')
        result += thing
        return result

    elif isinstance(thing, bytes):
        result = _bytes(unicode(len(thing)) + ':')
        result += thing
        return result

    elif isinstance(thing, bytearray):
        return bencode(bytes(thing))

    elif isinstance(thing, list):
        result = b'l'
        result += b''.join(bencode(i) for i in thing)
        result += b'e'
        return result

    elif isinstance(thing, dict):
        result = b'd'

        keys = list(thing.keys())
        keys.sort()

        for key in keys:
            result += bencode(key)
            result += bencode(thing[key])

        result += b'e'
        return result

    raise TypeError('bencoding objects of type "{type}" is not supported'.format(type=type(thing)))