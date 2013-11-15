from __future__ import print_function, unicode_literals, division, absolute_import
import os
import re
import logging
import subprocess

import config


class VideoFile(object):

    VALID_EXTENSIONS = (
        '.mkv',
        '.mp4',
        '.avi',
    )

    def __init__(self, path):

        path = os.path.expanduser(path)
        file_extension = os.path.splitext(path)[1]
        if (not os.path.isfile(path)) or (file_extension not in self.VALID_EXTENSIONS):
            raise VideoFileError('{path} is not a valid video file.'.format(path=path))

        self.path = os.path.abspath(path)
        self.screenshots = []

    def __repr__(self):
        return self.path

    def take_screenshots(self):
        pass

    def verify_screenshots(self):
        pass

    def delete_screenshots(self):
        pass

    def get_duration(self):
        """
        Get video duration in seconds.
        """

        command = '"{mediainfo}" "--Inform=Video;%Duration%" "{file}"'
        command = command.format(mediainfo=config.MEDIAINFO_PATH, file=self.path)
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError as e:
            msg = 'Could not get duration from mediainfo: {error_string}'
            raise VideoFileError(msg.format(error_string=e.output.decode(encoding='utf-8')))
        else:
            duration = int(output.decode(encoding='utf-8'))

        duration /= float(1000)
        msg = 'Video duration: {n} seconds'
        logging.debug(msg.format(n=duration))
        return duration

    def get_gop_duration(self):
        """
        Use key_frame interval (keyint) from encoding settings to calculate GOP duration.
             http://mewiki.project357.com/wiki/X264_Settings#keyint
             http://ffmpeg.org/trac/ffmpeg/wiki/Seeking%20with%20FFmpeg#Fastandaccurateseeking
        """

        encoding_settings = dict()
        command = '"{mediainfo}" "--Inform=Video;%Encoded_Library_Settings%" "{file}"'
        command = command.format(mediainfo=config.MEDIAINFO_PATH, file=self.path)

        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError as e:
            output = e.output.decode(encoding='utf-8')
            msg = 'Could not get encoding settings from mediainfo: {error_string}'
            logging.debug(msg.format(error_string=output))
        else:
            output = output.decode(encoding='utf-8').split(' / ')
            for setting in output:
                if '=' not in setting:
                    continue
                (key, delimiter, value) = setting.partition('=')
                encoding_settings[key] = value

        key_frame_interval = encoding_settings.get('keyint')

        if key_frame_interval is not None:
            # Get GOP size in seconds, assuming 25fps (Note: x264 default will be 10 seconds)
            gop_duration = int(key_frame_interval) // 25
        else:
            # Assume GOP size of 30 seconds, to be safe
            gop_duration = 30

        return gop_duration

    def get_playback_resolution(self):
        """
        If a SAR is applied to stretch the pixels during playback, we need to
        know the resulting resolution so we can take screenshots at the right AR.
        """

        command = '"{ffprobe}" "{file}"'.format(ffprobe=config.FFPROBE_PATH, file=self.path)

        # Get a description of the video stream from ffprobe
        logging.debug(command)
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError as e:
            msg = 'Error using ffprobe:\n{error_string}'
            raise VideoFileError(msg.format(error_string=e.output.decode(encoding='utf-8')))
        else:
            output = output.decode(encoding='utf-8')

        # The stream description will be in one of the following formats. (Also, "PAR" might appear as "SAR")
        #   Stream #0.0(eng): Video: h264 (High), yuv420p, 700x548 [PAR 64:45 DAR 2240:1233], PAR 199:140 DAR 995:548, 25 fps, 25 tbr, 1k tbn, 50 tbc (default)
        #   Stream #0.0(eng): Video: h264 (High), yuv420p, 1280x532, PAR 1:1 DAR 320:133, 23.98 fps, 23.98 tbr, 1k tbn, 47.95 tbc (default)
        match = re.search(r'(\d+)x(\d+) \[[SP]AR \d+:\d+ DAR (\d+):(\d+)\]', output)
        if match is None:
            match = re.search(r'(\d+)x(\d+), [SP]AR \d+:\d+ DAR (\d+):(\d+)', output)
        if match is None:
            return None

        stored_width = int(match.group(1))
        stored_height = int(match.group(2))
        dar_x = int(match.group(3))
        dar_y = int(match.group(4))

        # Ignore DAR if 1:1
        if dar_x == dar_y:
            return None

        playback_width = int((stored_height * dar_x) // dar_y)

        # Ignore if we are within 1 pixel already
        if abs(playback_width - stored_width) <= 1:
            return None

        # Frame size must be a multiple of 2
        if playback_width % 2 != 0:
            playback_width += 1

        playback_resolution = '{w}x{h}'.format(w=playback_width, h=stored_height)

        logging.info('Playback resolution: {r}'.format(r=playback_resolution))
        return playback_resolution


class VideoFileError(Exception):
    pass