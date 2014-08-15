from __future__ import print_function, unicode_literals, division, absolute_import
import tempfile
import logging
import hashlib
import shutil
import pprint
import math
import time
import os
import io

import trackers
import files


KB = 1024
MB = 1048576
GB = 1073741824


class Torrent(object):

    def __init__(self, release, tracker):

        self.release = release
        self.tracker = tracker

        assert isinstance(self.tracker, trackers.BaseTracker)

        if release.size == 0:
            raise TorrentError('Cannot make torrent; release size is zero bytes!')

        self.piece_size = self._select_piece_size(self.release.size)
        self.announce_url = self.tracker.announce_url
        self.extension_whitelist = self.tracker.FILE_EXTENSION_WHITELIST

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

    @staticmethod
    def _select_piece_size(size):
        """
        Pick a reasonable piece size, based on the size of the file(s)
        """

        if size >= (15 * GB):
            return 8 * MB

        elif size >= (7 * GB):
            return 4 * MB

        elif size >= (3 * GB):
            return 2 * MB

        else:
            return 1 * MB

    def move_to(self, destination):

        assert os.path.isfile(self.path)
        if not os.path.isdir(destination):
            msg = 'Destination "{path}" is not a directory!'
            raise TorrentError(msg.format(path=destination))

        file_name = os.path.basename(self.path)
        new_path = os.path.join(destination, file_name)

        msg = 'Moving torrent file "{torrent_file}" to "{destination}"'
        logging.info(msg.format(torrent_file=file_name, destination=destination))

        # Overwrite any existing torrent file at this path
        try:
            os.unlink(new_path)
        except OSError:
            pass

        shutil.move(self.path, destination)
        self.path = new_path

    def _create_metainfo_dict(self, include_md5_sum=True):

        if os.path.isfile(self.release.path):
            info = self._create_file_info_dict(
                file_path=self.release.path,
                piece_size=self.piece_size,
                include_md5_sum=include_md5_sum,
            )

        elif os.path.isdir(self.release.path):
            info = self._create_directory_info_dict(
                root_dir_path=self.release.path,
                piece_size=self.piece_size,
                include_md5_sum=include_md5_sum,
            )

        else:
            raise TorrentError(
                '"{path}" is not a file or directory!'.format(
                    path=self.release.path
                )
            )

        # Make this torrent private
        info['private'] = 1

        # Make the info hash unique to this tracker, to avoid
        # any cross-seeding issues
        info['created for'] = repr(self.tracker)

        metainfo = {
            'info':           info,
            'announce':       self.announce_url,
            'creation date':  int(time.time()),
            'created by':     'MacGuffin',
            'comment':        'https://github.com/hwkns/macguffin',
        }

        msg = 'Torrent metainfo dictionary:\n{metainfo}'
        logging.debug(msg.format(metainfo=pprint.pformat(metainfo)))

        return metainfo

    def _create_file_info_dict(self, file_path, piece_size, include_md5_sum=True):
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

        file_extension = os.path.splitext(file_path)[1].lower()
        if (self.extension_whitelist is not None) and (file_extension not in self.extension_whitelist):
            msg = '"{path}" is not a valid file type for upload to this tracker'
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

    def _create_directory_info_dict(self, root_dir_path, piece_size, include_md5_sum=True):
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

        if piece_size < (16 * KB):
            msg = 'Piece size {size} is less than 16 KiB!'
            raise TorrentError(msg.format(size=piece_size))

        # Concatenated 20-byte SHA-1 hashes of all the torrent's pieces.
        info_pieces = bytearray()

        # This bytearray will be used for the calculation of info_pieces.
        # Consecutive files will be written into data_buffer as a continuous
        # stream, as required by the BitTorrent specification.
        data_buffer = bytearray()

        file_dicts = []

        for (dir_path, dir_names, file_names) in os.walk(root_dir_path):

            for file_name in file_names:

                # If the file's extension isn't in the whitelist, ignore it
                file_extension = os.path.splitext(file_name)[1].lower()
                if (self.extension_whitelist is not None) and (file_extension not in self.extension_whitelist):
                    continue

                file_path = os.path.join(dir_path, file_name)

                # Build the current file's dictionary.
                file_dict = {
                    'length': os.path.getsize(file_path),
                    'path':   files.split_path(os.path.relpath(file_path, root_dir_path))
                }

                # Keep track of the file's MD5 sum
                md5 = hashlib.md5() if include_md5_sum else None

                logging.info(
                    'Hashing file "{path}"... '.format(
                        path=os.path.relpath(file_path, root_dir_path)
                    )
                )

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

    # Find the number of pieces in the file
    file_size = os.path.getsize(file_path)
    num_pieces = int(math.ceil(file_size / piece_size))

    # Yield pieces
    with io.open(file_path, mode='rb') as f:
        for __ in range(num_pieces):
            yield f.read(piece_size)


class TorrentError(Exception):
    pass
