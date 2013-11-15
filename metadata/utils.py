from __future__ import print_function, unicode_literals, division, absolute_import


class Sources:
    """
    Enum of all sources.
    """

    def __init__(self):
        raise NotImplementedError

    BLURAY = 0
    HDDVD = 1
    DVD = 2
    HDTV = 3
    WEBDL = 4
    CAM = 5
    SCREENER = 6
    R5 = 7
    OTHER = 8


class Resolutions:
    """
    Enum of all resolutions.
    """

    def __init__(self):
        raise NotImplementedError

    SD_480P = 0
    HD_720P = 1
    HD_1080P = 2


class Codecs:
    """
    Enum of all codecs.
    """

    def __init__(self):
        raise NotImplementedError

    X264 = 0
    XVID = 1
    DIVX = 2
    H264 = 3
    DVDR = 4
    MPEG2 = 5
    AVC = 6
    VC1 = 7


class Containers:
    """
    Enum of all containers.
    """

    def __init__(self):
        raise NotImplementedError

    AVI = 0
    MKV = 1
    MP4 = 2