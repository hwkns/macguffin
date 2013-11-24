from __future__ import print_function, unicode_literals, division, absolute_import
import tempfile
import logging
import hashlib
import shutil
import pprint
import time
import os
import io

import trackers
import files

KB = 1024
MB = 1048576
GB = 1073741824
FILE_EXTENSION_WHITELIST = ('.mkv', 'mp4', '.avi', '.ts', '.nfo', '.png', '.sub', '.idx', '.srt')


class Torrent(object):

    def __init__(self, release, tracker):

        if release.size == 0:
            raise TorrentError('Cannot make torrent; release size is zero bytes!')

        # Set piece size based on release size
        if release.size >= (15 * GB):
            self.piece_size = (8 * MB)
        elif release.size >= (7 * GB):
            self.piece_size = (4 * MB)
        elif release.size >= (3 * GB):
            self.piece_size = (2 * MB)
        else:
            self.piece_size = (1 * MB)

        assert isinstance(tracker, trackers.BaseTracker)
        self.announce_url = tracker.announce_url

        self.release = release

        file_name = '{name}.torrent'.format(name=self.release.name)
        tmp = tempfile.gettempdir()
        self.path = os.path.join(tmp, file_name)
        msg = 'Creating "{torrent_file}" with piece size {size} MiB'
        logging.info(msg.format(torrent_file=file_name, size=self.piece_size // MB))

        # Overwrite any existing torrent file at this path
        try:
            os.unlink(self.path)
        except OSError:
            pass

        # Create and write the torrent file
        metainfo = self._create_metainfo_dict()
        bencoded_metainfo = files.bencode(metainfo)
        with io.open(self.path, mode='wb') as f:
            f.write(bencoded_metainfo)

        logging.info('Torrent created successfully.')

    def move_to(self, destination):
        assert os.path.isfile(self.path)
        msg = 'Moving torrent file "{torrent_file}" to "{destination}"'
        logging.info(msg.format(torrent_file=os.path.basename(self.path), destination=destination))
        shutil.move(self.path, destination)

    def _create_metainfo_dict(self, include_md5_sum=True):
        if os.path.isfile(self.release.path):
            info = self._create_file_info_dict(self.release.path, self.piece_size, include_md5_sum)
        elif os.path.isdir(self.release.path):
            info = self._create_directory_info_dict(self.release.path, self.piece_size, include_md5_sum)
        else:
            raise TorrentError('"{path}" is not a file or directory!'.format(path=self.release.path))

        info['private'] = 1
        metainfo = {
            'info':           info,
            'announce':       self.announce_url,
            'creation date':  int(time.time()),
            'created by':     'MacGuffin',
            'comment':        'Created with MacGuffin',
        }

        msg = 'Torrent metainfo dictionary:\n{metainfo}'
        logging.debug(msg.format(metainfo=pprint.pformat(metainfo)))

        return metainfo

    @staticmethod
    def _create_file_info_dict(file_path, piece_size, include_md5_sum=True):
        """
        Returns a dictionary with the following keys:
             - pieces: concatenated 20-byte SHA-1 hashes
             - name:   basename of the file
             - length: size of the file in bytes
             - md5sum: md5sum of the file (if include_md5_sum is True)
        @rtype: dict
        """
        if not os.path.isfile(file_path):
            msg = '"{path}" is not a file'
            raise TorrentError(msg.format(path=file_path))

        if os.path.getsize(file_path) == 0:
            msg = '"{path}" is a zero byte file!'
            raise TorrentError(msg.format(path=file_path))

        # Concatenated 20-byte SHA-1 hashes of all the file's pieces
        pieces = bytearray()

        # Aggregate MD5 sum
        md5 = hashlib.md5() if include_md5_sum else None

        msg = 'Hashing file "{path}"... '
        logging.info(msg.format(path=file_path))

        file_pieces = create_piece_generator(file_path, piece_size)
        for piece in file_pieces:

            piece_hash = files.sha1(piece)
            pieces.extend(piece_hash)

            if include_md5_sum:
                md5.update(piece)

        info = {
            'pieces':        pieces,
            'piece length':  piece_size,
            'name':          os.path.basename(file_path),
            'length':        os.path.getsize(file_path),
        }

        if include_md5_sum:
            info['md5sum'] = md5.hexdigest()

        assert len(info['pieces']) % 20 == 0, 'len(pieces) is not a multiple of 20 bytes!'

        return info

    @staticmethod
    def _create_directory_info_dict(root_dir_path, piece_size, include_md5_sum=True):
        """
        Returns a dictionary with the following keys:
             - pieces: concatenated 20-byte SHA-1 hashes
             - name:   basename of the directory (default name of all torrents)
             - files:  a list of dictionaries with the following keys:
                 - length: size of the file in bytes
                 - md5sum: md5 sum of the file (unless disabled via include_md5)
                 - path:   list of the file's path components, relative to the directory
        @rtype: dict
        """
        if not os.path.isdir(root_dir_path):
            msg = '"{path}" is not a directory'
            raise TorrentError(msg.format(path=root_dir_path))

        # Concatenated 20-byte SHA-1 hashes of all the torrent's pieces.
        info_pieces = bytearray()

        # This bytearray will be used for the calculation of info_pieces. Consecutive files will be
        # written into data_buffer as a continuous stream, as required by the BitTorrent specification.
        data_buffer = bytearray()

        file_dicts = []

        for (dir_path, dir_names, file_names) in os.walk(root_dir_path):

            for file_name in file_names:

                # If the file's extension isn't in the whitelist, ignore it
                if os.path.splitext(file_name)[1].lower() not in FILE_EXTENSION_WHITELIST:
                    continue

                file_path = os.path.join(dir_path, file_name)

                # Build the current file's dictionary.
                file_dict = {
                    'length': os.path.getsize(file_path),
                    'path':   files.split_path(os.path.relpath(file_path, root_dir_path))
                }

                # Keep track of the file's MD5 sum
                md5 = hashlib.md5() if include_md5_sum else None

                logging.info('Hashing file "{path}"... '.format(path=os.path.relpath(file_path, root_dir_path)))

                file_pieces = create_piece_generator(file_path, piece_size)
                for piece in file_pieces:
                    data_buffer.extend(piece)
                    if len(data_buffer) >= piece_size:
                        piece_hash = files.sha1(data_buffer[:piece_size])
                        info_pieces.extend(piece_hash)
                        data_buffer[:] = data_buffer[piece_size:]
                    if include_md5_sum:
                        md5.update(piece)

                if include_md5_sum:
                    file_dict['md5sum'] = md5.hexdigest()

                file_dicts.append(file_dict)

        # Hash any remaining data that is fewer than piece_size bytes
        if len(data_buffer) > 0:
            piece_hash = files.sha1(data_buffer)
            info_pieces.extend(piece_hash)

        info = {
            'pieces':        info_pieces,
            'piece length':  piece_size,
            'name':          os.path.basename(root_dir_path.strip(os.path.sep)),
            'files':         file_dicts,
        }

        assert len(info['pieces']) % 20 == 0, 'len(pieces) is not a multiple of 20 bytes!'

        return info


def create_piece_generator(file_path, piece_size):
    with io.open(file_path, mode='rb') as f:
        while True:
            piece_data = f.read(piece_size)
            if not piece_data:
                break
            yield piece_data


class TorrentError(Exception):
    pass