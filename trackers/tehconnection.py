from __future__ import print_function, unicode_literals, division, absolute_import
import logging
import pprint
import sys
import io

try:
    from bs4 import BeautifulSoup
except ImportError:
    logging.critical('You must install "beautifulsoup4" for this script to work.  Try "pip install beautifulsoup4".')
    sys.exit(1)

from .tracker import BaseTracker, TrackerError
import metadata
import config

if sys.version_info[0] >= 3:
    raw_input = input


class TehConnection(BaseTracker):

    # The file extensions allowed in TC torrents
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

    # The video containers allowed on TC
    CONTAINER_WHITELIST = {
        metadata.Containers.MKV,
        metadata.Containers.AVI,
    }

    # The container strings TC's upload form expects
    CONTAINER_STRING = {
        metadata.Containers.MKV: 'Matroska',
        metadata.Containers.AVI: 'AVI',
    }

    # The source strings TC's upload form expects
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

    # The codec strings TC's upload form expects
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

    # Release groups specifically banned at TC
    BANNED_GROUPS = {
        'aXXo',
        'DEViSE',
        'FLAWL3SS',
        'FZHD',
        'KingBen',
        'KLAXXON',
        'LTRG',
        'NhaNc3',
        'PRODJi',
        'SANTi',
        'VAMPS',
        'WHiiZz',
        'ERODELUXE',  # Softcore porn group
    }

    def __init__(self):

        super(TehConnection, self).__init__()

        if not (config.TC_USERNAME and config.TC_PASSWORD and config.TC_PASSKEY):
            raise TrackerError('You must specify your TC username, password, and torrent passkey in config.py')

        self.base_url = 'https://tehconnection.eu/'
        self.announce_url = 'http://tehconnection.eu:2790/{passkey}/announce'.format(passkey=config.TC_PASSKEY)

    def login(self):
        """
        Log in to the tracker (if necessary) and get cookies
        """

        # Send a HEAD request to upload.php to see if we're already logged in
        response = self.request('upload.php', method='HEAD', verify=False, allow_redirects=False)
        if response.status_code == 200:
            return True

        # POST credentials to login.php
        msg = 'Logging in to {site}'
        logging.debug(msg.format(site=self))
        self.session.cookies.clear()
        post_data = {
            'keeplogged': 1,
            'login': 'Log In!',
            'password': config.TC_PASSWORD,
            'username': config.TC_USERNAME,
        }
        response = self.request('login.php', method='POST', data=post_data, verify=True)

        # If we didn't get redirected, something went wrong
        if not response.history:
            soup = BeautifulSoup(response.text)
            error_message = soup.find('span', class_='warning')
            if error_message:
                logging.error(error_message.string.strip())
            raise TrackerError('Login failed!')

        # Save cookies so we can short-circuit next time
        self.session.cookies.save()

        return True

    def get_torrent_group(self, imdb_object):
        """
        Ask the tracker for the group ID for this film
        """

        # Log in to get new cookies if necessary
        self.login()

        params = {
            'action': 'get_group',
            'imdb': imdb_object.int_id
        }
        response = self.request('upload.php', params=params, verify=False)
        response_json = response.json()

        if response_json['status'] == 'error':
            msg = 'Error using get_torrent_group API: {error}'
            raise TrackerError(msg.format(error=response_json['error']))

        group_id = response_json['group_id']
        if group_id:
            msg = 'Found existing torrent group: {base_url}torrents.php?id={group_id}'
            logging.info(msg.format(base_url=self.base_url, group_id=group_id))
            return group_id
        else:
            msg = 'Did not find any existing torrent group for {imdb}'
            logging.info(msg.format(imdb=imdb_object))
            return None

    def dupe_check(self, release):
        """
        Ask the tracker for any similar releases that already exist
        """

        # Log in to get new cookies if necessary
        self.login()

        params = {
            'action': 'dupe_check',
            'group': release.torrent_group_id,
            'scene': 1 if release.is_scene else 0,
            'resolution': release.resolution,
            'codec': self.CODEC_STRING[release.codec]
        }

        msg = 'Checking for dupes using {params}'
        logging.debug(msg.format(params=params))

        response = self.request('upload.php', params=params, verify=False)
        response_json = response.json()

        if response_json['status'] == 'error':
            msg = 'Error using dupe_check: {error}'
            raise TrackerError(msg.format(error=response_json['error']))
        possible_dupes = response_json['releases']

        return possible_dupes

    @staticmethod
    def generate_bbcode(upload):

        bbcode = ''

        if upload.screenshots is not None and upload.screenshots.uploaded is True:
            bbcode += '[center][spoiler=Screenshots]'
            bbcode += upload.screenshots.bbcode
            bbcode += '[/spoiler][/center]\n'

        if upload.nfo is not None:
            bbcode += '[spoiler=NFO][size=2][pre]'
            bbcode += upload.nfo.text
            bbcode += '[/pre][/size][/spoiler]\n'

        return bbcode

    def take_upload(self, upload, dry_run=False):

        # Banned container check, banned release group check
        self.check_upload(upload)

        # Generate torrent description
        upload.torrent_description = self.generate_bbcode(upload)

        # Try to use a genre as the category; otherwise, use "Musical"
        category = None
        for genre in upload.imdb.genres:
            try:
                category = CATEGORY_ID[genre]
                break
            except KeyError:
                continue
        if category is None and 'Horror' in upload.imdb.genres:
            category = CATEGORY_ID['Thriller']
        if category is None:
            category = CATEGORY_ID['Musical']

        # Log in to get new cookies if necessary
        self.login()

        # Tell TC's retard code to fetch rating and peoples info for the film
        msg = 'Asking {site} to update IMDb data for this film.'
        logging.debug(msg.format(site=self))
        params = {
            'id': upload.imdb.int_id
        }
        self.request('imdb.php', params=params, verify=False)

        torrent_file = {
            'file_input': io.open(upload.torrent.path, mode='rb')
        }

        data = {

            # Form submitted (always true)
            'submit': 'true',

            # Main category (just pick a genre from IMDb that works)
            'type': category,

            # Poster image URL (use TMDB)
            'image': upload.tmdb.poster_url,

            # Film title
            'title': upload.title,

            # Film release year
            'year': upload.year,

            # Codec
            'format': self.CODEC_STRING[upload.codec],

            # Container
            'container': self.CONTAINER_STRING[upload.container],

            # Resolution
            'bitrate': upload.resolution,

            # Source media
            'media': self.SOURCE_STRING[upload.source],

            # Film description
            'album_desc': upload.film_description,

            # Release name
            'release_name': upload.release.name,

            # Mediainfo output
            'mediainfo': upload.mediainfo.text,

            # Release description (screenshots, NFO)
            'release_desc': upload.torrent_description
        }

        for genre in upload.imdb.genres:
            gid = GENRE_ID.get(genre)
            if gid is not None:
                data['genre_' + gid] = gid

        if upload.imdb.id:
            data['hasimdb'] = 'true'
            data['imdb_number'] = upload.imdb.int_id

        if upload.release.is_scene:
            data['scene'] = 'true'

        msg = 'Uploading {release} to {site}'
        logging.info(msg.format(release=upload.release, site=self))
        msg = 'Upload form data:\n{form_fields}'
        logging.debug(msg.format(form_fields=pprint.pformat(data)))

        if dry_run:

            logging.info('Skipping actual upload -- this is a dry run!')

        else:

            # Post the upload form
            response = self.request('upload.php', method=b'POST', data=data, files=torrent_file, verify=False)

            if not response.history:

                # Log any errors displayed by the upload form
                soup = BeautifulSoup(response.text)
                error_elements = soup.find_all('p', style='color: red;text-align:center;')
                for error in error_elements:
                    logging.error(error.string.strip())

                raise TrackerError('Upload failed!')

            else:

                msg = 'Upload complete: {url}'
                logging.info(msg.format(url=response.url))

        torrent_file['file_input'].close()


CATEGORY_ID = {
    'Action':      '0',
    'Comedy':      '1',
    'Documentary': '2',
    'Drama':       '3',
    'Musical':     '4',
    'Thriller':    '5'
}

GENRE_ID = {
    'Action':      '132951',
    'Adventure':   '122473',
    'Animation':   '122474',
    'Anime':       '122513',
    'Biography':   '122475',
    'Comedy':      '122494',
    'Crime':       '122476',
    'Documentary': '132953',
    'Drama':       '132952',
    'Family':      '122477',
    'Fantasy':     '122478',
    'Film-Noir':   '122479',
    'Foreign':     '122493',
    'History':     '122480',
    'Horror':      '122481',
    'Indie':       '122495',
    'Music':       '132956',
    'Musical':     '132954',
    'Mystery':     '122483',
    'Political':   '122484',
    'Romance':     '122485',
    'Sci-Fi':      '122486',
    'Short':       '122487',
    'Sport':       '122488',
    'Stand-Up':    '138520',
    'Thriller':    '132955',
    'War':         '122489',
    'Western':     '122490'
}