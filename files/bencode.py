from __future__ import print_function, unicode_literals, division, absolute_import
import sys

if sys.version_info[0] >= 3:
    unicode = str
    long = int


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
    if isinstance(thing, (int, long)):
        result = _bytes('i{thing}e'.format(thing=thing))

    elif isinstance(thing, unicode):
        result = bencode(_bytes(thing))

    elif isinstance(thing, bytes):
        result = _bytes(unicode(len(thing)))
        result += b':'
        result += thing

    elif isinstance(thing, bytearray):
        result = bencode(bytes(thing))

    elif isinstance(thing, list):
        result = b'l'
        for item in thing:
            result += bencode(item)
        result += b'e'

    elif isinstance(thing, dict):
        keys = list(thing.keys())
        keys.sort()

        result = b'd'
        for key in keys:
            result += bencode(key)
            result += bencode(thing[key])
        result += b'e'

    else:
        raise TypeError('bencoding objects of type "{type}" is not supported'.format(type=type(thing)))

    assert isinstance(result, bytes), 'Not bytes: [{type}] {result}'.format(type=type(result), result=result)
    return result