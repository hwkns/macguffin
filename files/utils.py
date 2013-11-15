from __future__ import print_function, unicode_literals, division, absolute_import
import os
import string
import random
import logging
import subprocess
from io import StringIO

import config


def valid_path(path):
    """
    Returns an expanded, absolute path, or None if the path does not exist.
    """
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return None
    return os.path.abspath(path)


def get_paths(args):
    """
    Returns expanded, absolute paths for all valid paths in a list of arguments.
    """
    assert isinstance(args, list)
    valid_paths = []
    for path in args:
        abs_path = valid_path(path)
        if abs_path is not None:
            valid_paths.append(abs_path)
    return valid_paths


def generate_id(size=10, chars=string.ascii_uppercase + string.digits):
    """
    Generate a string of random alphanumeric characters.
    """
    return ''.join(random.choice(chars) for i in range(size))


def list_contents(rar_file_path):
    """
    Returns a list of the archive's contents.
    """

    assert os.path.isfile(rar_file_path) and rar_file_path.endswith('.rar')

    contents = []
    count = 0
    command = '"{unrar}" v -- "{file}"'
    command = command.format(unrar=config.UNRAR_PATH, file=rar_file_path)

    try:

        output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)

    except subprocess.CalledProcessError as e:

        output = e.output.decode(encoding='utf-8')
        msg = 'Error while listing archive contents: "{error_string}"'
        raise FileUtilsError(msg.format(error_string=output.strip()))

    else:

        output = StringIO(output.decode(encoding='utf-8'))
        parse = False
        for line in output.readlines():
            line_list = line.strip().split()
            # If the line is not empty...
            if line_list:
                # This marks the start and end of the section we want to parse
                if line_list[0] == '-------------------------------------------------------------------------------':
                    parse = not parse
                    count = 0
                # If we're in the section of the output we want to parse...
                elif parse:
                    # Parse every other line (only the file paths)
                    if count % 2 == 0:
                        contents.append(line_list[0])
                    count += 1

    return contents


def unrar(rar_file_path, destination_dir=None):
    """
    Get a list of the archive's contents, then extract the archive and return the list.
    """

    assert os.path.isfile(rar_file_path) and rar_file_path.endswith('.rar')

    if not destination_dir:
        destination_dir = os.path.split(rar_file_path)[0]

    # Get a list of the archive's contents
    contents = list_contents(rar_file_path)
    extracted_files = []

    # Extract the archive
    command = '"{unrar}" x -o+ -- "{file}" "{destination}"'
    command = command.format(unrar=config.UNRAR_PATH, file=rar_file_path, destination=destination_dir)
    logging.debug(command)

    try:
        subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        output = e.output.decode(encoding='utf-8')
        msg = 'Error while extracting!\n{error_string}'
        raise FileUtilsError(msg.format(error_string=output.strip()))

    for relative_path in contents:

        path = os.path.join(destination_dir, relative_path)

        # Recursively extract until there are no RAR files left
        if path.endswith('.rar'):
            extracted_files += unrar(path)
        else:
            extracted_files.append(path)

    # Return the list of paths
    return extracted_files


class FileUtilsError(Exception):
    pass