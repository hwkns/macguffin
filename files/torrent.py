from __future__ import print_function, unicode_literals, division, absolute_import
import os
import shutil
import logging
import subprocess
import tempfile
import math

import trackers
import config

GB = 1073741824


class Torrent(object):

    def __init__(self, release, tracker):

        # TODO: add a comment and use that in the hash to ease cross-seeding?

        if release.size == 0:
            raise TorrentError('Cannot make torrent; release size is zero bytes!')
        else:
            # Set piece size based on release size
            #  15 GB+ => 8 MB pieces (23)
            #  7  GB+ => 4 MB pieces (22)
            #  3  GB+ => 2 MB pieces (21)
            #  0  GB+ => 1 MB pieces (20)
            self.piece_size = int(math.log(release.size + (1 * GB), 2) - 11)
            self.piece_size = max(20, self.piece_size)
            self.piece_size = min(23, self.piece_size)

        assert isinstance(tracker, trackers.BaseTracker)
        self.announce_url = tracker.announce_url

        file_name = '{name}.torrent'.format(name=release.name)
        tmp = tempfile.gettempdir()
        self.path = os.path.join(tmp, file_name)

        # Overwrite any existing torrent file at this path
        try:
            os.unlink(self.path)
        except OSError:
            pass

        # Start constructing the mktorrent command line; set the private flag
        self.command = '"{mktorrent}" -p'.format(mktorrent=config.MKTORRENT_PATH)

        # Set the announce URL
        self.command += ' -a "{announce_url}"'.format(announce_url=self.announce_url)

        # Set the number of threads
        if config.MKTORRENT_THREADS and 0 < config.MKTORRENT_THREADS < 20:
            self.command += ' -t {threads}'.format(threads=config.MKTORRENT_THREADS)

        # Set the piece size
        self.command += ' -l {piece_size}'.format(piece_size=self.piece_size)

        # Set the output file path
        self.command += ' -o "{output_file}"'.format(output_file=self.path)

        # Set the input file/dir
        self.command += ' "{input_file}"'.format(input_file=release.path)

        # Make the torrent; check for errors
        msg = 'Creating torrent "{torrent_file}"'
        logging.info(msg.format(torrent_file=self.path))
        logging.debug(self.command)
        try:
            subprocess.check_output(self.command, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError as e:
            error_output = e.output.decode(encoding='utf-8')
            raise TorrentError(error_output.split('\n')[0])
        else:
            logging.info('Torrent created successfully.')

    def move_to(self, destination):
        assert os.path.isfile(self.path)
        msg = 'Moving torrent file "{torrent_file}" to "{destination}"'
        logging.info(msg.format(torrent_file=os.path.split(self.path)[1], destination=destination))
        shutil.move(self.path, destination)


class TorrentError(Exception):
    pass