from __future__ import print_function, unicode_literals, division, absolute_import
import os
import logging
import re

import files
import metadata
import uploads


class Release(object):
    """
    This class represents a file or directory structure that constitutes a Scene or P2P release of a film.
    """

    def __init__(self, path=None, name=None):

        if path is not None:

            path = os.path.expanduser(path)

            # Make sure the path provided to the script is acceptable
            if os.path.isdir(path):

                # This is a directory
                self.is_single_file = False
                logging.debug('The provided path is a directory.')

                self.path = os.path.abspath(path)
                (self.base_path, self.folder_name) = os.path.split(self.path)
                msg = 'Base path:  {path}'
                logging.debug(msg.format(path=self.base_path))
                msg = 'Folder name: {folder}'
                logging.debug(msg.format(folder=self.folder_name))

                # Get release name; take the folder name, and replace any spaces with dots
                self.name = self.folder_name.replace(' ', '.')

            elif os.path.isfile(path):

                # This is a file
                self.is_single_file = True
                logging.debug('The provided path is a single file.')

                self.path = os.path.abspath(path)
                (self.base_path, self.folder_name) = os.path.split(self.path)

                (file_base_name, extension) = os.path.splitext(self.folder_name)

                if extension not in VIDEO_EXTENSION_WHITELIST:
                    msg = 'The path "{path}" does not have an extension in {whitelist}.'
                    raise ReleaseError(msg.format(path=path, whitelist=VIDEO_EXTENSION_WHITELIST))
                else:
                    msg = 'File name: {file}'
                    logging.debug(msg.format(file=self.folder_name))

                # Get release name; take the file's base name, and replace any spaces with dots
                self.name = file_base_name.replace(' ', '.')

            else:

                # This path does not exist
                msg = 'The path "{path}" is not a file or directory.'
                raise ReleaseError(msg.format(path=path))

        elif name is not None:

            self.name = name.replace(' ', '.')
            self.base_path = None
            self.folder_name = None
            self.path = None
            self.is_single_file = False

        else:

            raise ReleaseError('No path or release name provided!')

        self.edition = 'Theatrical'
        self.is_scene = None
        self.video_file = None
        self.size = 0

        self.title = None
        self.year = None
        self.codec = None
        self.container = None
        self.source = None
        self.resolution = None
        self.group = None

        self.parse_release_name()

    def __repr__(self):
        if self.size != 0:
            return '{name} ({size})'.format(name=self.name, size=self.get_size())
        else:
            return self.name

    def get_size(self):
        """
        Get the human readable size of this release.
        """

        if self.size == 0:
            return 'unknown size'

        size = self.size
        steps = 0

        units = ('B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB')
        while size > 1024:
            steps += 1
            size /= float(1024)

        return '{size} {units}'.format(size=round(size, 3), units=units[steps])

    def parse_release_name(self):
        """
        Parse out the title, year, codec, source media, and resolution from the release name.
        """

        # Get title from release name
        self.title = get_title(self.name)
        if self.title is not None:
            msg = 'Title: {title}'
            logging.debug(msg.format(title=self.title))
        else:
            msg = 'Unable to parse title from release name "{name}"'
            raise ReleaseError(msg.format(name=self.name))

        # Get year from release name
        self.year = get_year(self.name)
        if self.year is not None:
            msg = 'Year: {year}'
            logging.debug(msg.format(year=self.year))
        else:
            msg = 'Unable to parse year from release name "{name}"'
            logging.warning(msg.format(name=self.name))

        # Get codec from release name
        self.codec = get_codec(self.name)
        if self.codec is not None:
            msg = 'Codec: {codec}'
            logging.debug(msg.format(codec=self.codec))
        else:
            msg = 'Unable to parse codec from release name "{name}"'
            raise ReleaseError(msg.format(name=self.name))

        # Get source media from release name
        self.source = get_source(self.name)
        if self.source is None:
            msg = 'Unable to parse source from release name "{name}"'
            raise ReleaseError(msg.format(name=self.name))

        # Get resolution from release name
        self.resolution = get_resolution(self.name)
        if self.resolution is not None:
            msg = 'Resolution: {resolution}'
            logging.debug(msg.format(resolution=self.resolution))
        else:
            self.resolution = 'Standard Def'

        # Get group name from release name
        self.group = get_group(self.name)
        if self.group is not None:
            msg = 'Release group: {group}'
            logging.debug(msg.format(group=self.group))
        else:
            msg = 'Unable to parse release group from release name "{name}"'
            logging.debug(msg.format(name=self.name))

        # Decide Scene or P2P based on release group
        if self.group in metadata.scene_groups or uploads.check_predb(self.name):
            self.is_scene = True
        elif self.group in metadata.p2p_groups:
            self.is_scene = False
        else:
            self.is_scene = None

    def find_unwanted_files(self, extension_whitelist=None):
        """
        Get a list of all files in this release with extensions that are not whitelisted.
        """

        unwanted_files = []

        if self.is_single_file or self.path is None or extension_whitelist is None:
            return []

        for (dir_path, dir_names, file_names) in os.walk(self.path, onerror=report_listdir_error):
            for file_name in file_names:
                # If the file's extension is not in the whitelist...
                file_extension = os.path.splitext(file_name)[1].lower()
                if file_extension not in extension_whitelist:
                    path = os.path.join(dir_path, file_name)
                    unwanted_files.append(path)

        return unwanted_files

    def clean_up(self, delete_unwanted_files=False, extension_whitelist=None):
        """
        Extract RAR files and remove unwanted files.
        """

        if self.is_single_file or self.path is None:
            return

        # Extract all RAR files in place
        self.unrar()

        # Remove any non-whitelisted files
        if delete_unwanted_files is True:
            for path in self.find_unwanted_files(extension_whitelist=extension_whitelist):
                msg = 'Deleting non-whitelisted file "{file}"'
                logging.debug(msg.format(file=path))
                os.unlink(path)

        # Remove any empty directories
        for (dir_path, dir_names, file_names) in os.walk(self.path, topdown=False, onerror=report_listdir_error):
            for name in dir_names:
                try:
                    d = os.path.join(dir_path, name)
                    os.rmdir(d)
                    msg = 'Deleting empty directory "{dir}"'
                    logging.debug(msg.format(dir=d))
                except OSError:
                    pass

    def unrar(self, destination_base_path=None):
        """
        Extract all RAR archives present in the release to the specified destination.
        """

        if self.is_single_file:
            return

        if destination_base_path is None:
            destination_base_path = self.path

        msg = 'Extracting any RAR files. Destination base path: "{path}"'
        logging.debug(msg.format(path=destination_base_path))
        for (dir_path, dir_names, file_names) in os.walk(self.path, onerror=report_listdir_error):
            for file_name in file_names:

                if file_name.endswith('.rar'):

                    # Sort out absolute and release-relative paths
                    rar_file_path = os.path.join(dir_path, file_name)
                    sub_path = re.sub(self.path, '', dir_path)
                    destination_path = destination_base_path + sub_path

                    # Extract the RAR archive
                    msg = 'Extracting "{file}"'
                    logging.info(msg.format(file=os.path.join(sub_path, file_name)))
                    try:
                        extracted_files = files.unrar(rar_file_path, destination_path)
                    except files.FileUtilsError as e:
                        raise ReleaseError(e)
                    else:
                        for path in extracted_files:
                            logging.info('-> ' + path)

    def get_nfo(self):

        if self.is_single_file or self.path is None:
            return None

        nfo_files = []

        for (dir_path, dir_names, file_names) in os.walk(self.path, onerror=report_listdir_error):

            for file_name in file_names:
                path = os.path.join(dir_path, file_name)
                file_size = os.path.getsize(path)

                if file_name.endswith('.nfo'):
                    nfo_files.append((file_size, path))

        if nfo_files:

            # Pick the largest file
            nfo_file = sorted(nfo_files, reverse=True)[0][1]
            msg = 'Found NFO: {file_name}'
            logging.debug(msg.format(file_name=os.path.split(nfo_file)[1]))

            try:
                nfo = files.NFO(nfo_file)
            except files.NFOError:
                return None

            return nfo

        else:

            logging.debug('No NFO file found')
            return None

    def find_video_file(self):

        if self.is_single_file:
            self.video_file = self.path
            self.size = os.path.getsize(self.path)
            if self.video_file.endswith('.mkv'):
                self.container = metadata.Containers.MKV
            elif self.video_file.endswith('mp4'):
                self.container = metadata.Containers.MP4
            elif self.video_file.endswith('.avi'):
                self.container = metadata.Containers.AVI
            return

        video_files = []

        for (dir_path, dir_names, file_names) in os.walk(self.path, onerror=report_listdir_error):

            for file_name in file_names:
                path = os.path.join(dir_path, file_name)
                file_size = os.path.getsize(path)

                file_extension = os.path.splitext(path)[1]
                if file_extension in VIDEO_EXTENSION_WHITELIST:
                    video_files.append((file_size, path))

                self.size += file_size

        if video_files:

            self.video_file = sorted(video_files, reverse=True)[0][1]
            if self.video_file.endswith('.mkv'):
                self.container = metadata.Containers.MKV
            elif self.video_file.endswith('.mp4'):
                self.container = metadata.Containers.MP4
            elif self.video_file.endswith('.avi'):
                self.container = metadata.Containers.AVI
            msg = 'Found main video file: {file_name}'
            logging.debug(msg.format(file_name=os.path.split(self.video_file)[1]))

        else:

            raise ReleaseError('Could not find video file!')


def get_title(release_name):
    """
    Parse the release name and return the film's title.  If no title is found, return None.
    """
    title = NON_TITLE_REGEX.sub('', release_name).replace('.', ' ')
    if title.strip() == '':
        return None
    else:
        return title


def get_year(release_name):
    """
    Parse the release name and return the film's year.  If no year is found, return None.
    """
    year = YEAR_REGEX.search(release_name)
    if year is None:
        return None
    else:
        return year.group().strip('.').lstrip('(').rstrip(')')


def get_codec(release_name):
    """
    Parse the release name and return the film's codec.  If no codec is found, return None.
    """
    codec = FORMAT_REGEX.search(release_name)
    if codec is None:
        return None
    else:
        codec = codec.group().strip('.').strip('-').lower()
        return CODEC.get(codec)


def get_source(release_name):
    """
    Parse the release name and return the film's source media.  If no source is found, return None.
    """
    source = SOURCE_REGEX.search(release_name)
    if not source:
        return None
    else:
        source = source.group().strip('.').strip('-').lower()
        if source == 'brrip':
            raise ReleaseError('BRRips are an abomination.')
        return SOURCE.get(source)


def get_resolution(release_name):
    """
    Parse the release name and return the film's resolution.  If no resolution is found, return None.
    """
    resolution = RESOLUTION_REGEX.search(release_name)
    if not resolution:
        return None
    else:
        return resolution.group().strip('.').strip('-')


def get_group(release_name):
    """
    Parse the release name and return the release group.  If no group name is found, return None.
    """
    group_name = GROUP_REGEX.search(release_name)
    if not group_name:
        return None
    else:
        return group_name.group().strip('-')


def report_listdir_error(os_error):
    """
    Error handling function for os.walk().
    """
    msg = 'Could not list directory "{dir}".  Check file permissions.'
    raise ReleaseError(msg.format(dir=os_error.filename))


class ReleaseError(Exception):
    pass


# Whitelist for video file extensions (used for single file releases)
VIDEO_EXTENSION_WHITELIST = ('.mkv', 'mp4', '.avi')


# Regular expressions for parsing the release name
NON_TITLE_REGEX = re.compile(r'\.(?:\(?(?:19|20)[0-9]{2}\)?|480p|576p|720p|1080p|1080i|NTSC|PAL|STV|PPF|R5|DVDSCR|SCREENER|DVDRip|BDRip|LIMITED|COMPLETE|PROPER|REPACK|RERiP|TS|TELESYNC|CAM|FESTIVAL|SUBBED)\..*')
YEAR_REGEX = re.compile(r'\.(\(?(?:19|20)[0-9]{2}\)?)(\.|\-|$)')
SOURCE_REGEX = re.compile(r'\.(NTSC|PAL|R[56C]|TS|CAM|TELESYNC|SCREENER|DVDSCR|BDRip|Blu\-?Ray|HDDVD|DVDRip|DVDR?|HDTV|WEB-DL|WEBRip|DTheater|TVRip)(\.|\-|$)', re.IGNORECASE)
FORMAT_REGEX = re.compile(r'\.(XViD|x264|DVDR|VIDEO_TS|H\.?264|MPEG2|AVC)(\-|\.|$)', re.IGNORECASE)
RESOLUTION_REGEX = re.compile(r'\.(1080p|1080i|720p|480p|576p)(\.|\-|$)')
GROUP_REGEX = re.compile(r'\-([^\.]*)$')


# This dict maps lowercase regex-matched sources to the Sources enum value
SOURCE = {
    'bluray': metadata.Sources.BLURAY,
    'blu-ray': metadata.Sources.BLURAY,
    'bdrip': metadata.Sources.BLURAY,
    'hddvd': metadata.Sources.HDDVD,
    'dvdrip': metadata.Sources.DVD,
    'dvd': metadata.Sources.DVD,
    'dvdr': metadata.Sources.DVD,
    'pal': metadata.Sources.DVD,
    'ntsc': metadata.Sources.DVD,
    'hdtv': metadata.Sources.HDTV,
    'web-dl': metadata.Sources.WEBDL,
    'webrip': metadata.Sources.OTHER,
    'cam': metadata.Sources.CAM,
    'ts': metadata.Sources.CAM,
    'screener': metadata.Sources.SCREENER,
    'dvdscr': metadata.Sources.SCREENER,
    'r5': metadata.Sources.R5,
    'r6': metadata.Sources.OTHER,
    'rc': metadata.Sources.OTHER,
    'dtheater': metadata.Sources.OTHER,
    'tvrip': metadata.Sources.OTHER,
}


# This dict maps lowercase regex-matched codecs to the Codecs enum value
CODEC = {
    'x264': metadata.Codecs.X264,
    'xvid': metadata.Codecs.XVID,
    'divx': metadata.Codecs.DIVX,
    'h264': metadata.Codecs.H264,
    'h.264': metadata.Codecs.H264,
    'dvdr': metadata.Codecs.DVDR,
    'video_ts': metadata.Codecs.DVDR,
    'mpeg2': metadata.Codecs.MPEG2,
    'avc': metadata.Codecs.AVC,
    'vc-1': metadata.Codecs.VC1,
}


# File extension whitelists for source uploads (these are not used, but might be in the future)

DVD_EXTENSIONS = (
    '.iso',
    '.bup',
    '.ifo',
    '.vob'
)

BD_EXTENSIONS = (
    '.inf',
    '.sig',
    '.crt',
    '.crl',
    '.bdmv',
    '.m2ts',
    '.mpls',
    '.xml',
    '.jpg',
    '.properties',
    '.jar',
    '.png',
    '.clpi',
    '.bdjo',
    '.cci',
    '.lst',
    '.tbl',
    '.cer'
)