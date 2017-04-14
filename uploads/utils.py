# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, division, absolute_import
from difflib import SequenceMatcher
import logging
import string
import sys

try:
    from bs4 import BeautifulSoup
except ImportError:
    logging.critical('You must install "beautifulsoup4" for this script to work.  Try "pip install beautifulsoup4".')
    sys.exit(1)

try:
    import requests
except ImportError:
    logging.critical('You must install "requests" for this script to work.  Try "pip install requests".')
    sys.exit(1)


def normalize_title(s):
    """
    Convert to lowercase and remove punctuation characters.
    """
    s = s.replace('&', 'and')
    s = s.replace('.', ' ')
    return ''.join(char for char in s.lower() if char not in string.punctuation)


def strings_match(string_a, string_b):
    """
    Return True if strings are at least 90% similar, False otherwise.

    Arguments can each be either a single string or a list of possible matching strings.
    """

    if isinstance(string_a, list):
        return any(
            strings_match(item, string_b)
            for item in string_a
        )

    if isinstance(string_b, list):
        return any(
            strings_match(string_a, item)
            for item in string_b
        )

    matcher = SequenceMatcher(None, string_a, string_b)
    return matcher.ratio() >= 0.90


def years_match(year_a, year_b):
    """
    Returns True if year_a and year_b are no more than 1 year apart, False otherwise.
    """
    return any(
        year_a == str(int(year_b) + i)
        for i in (-1, 0, 1)
    )


def check_predb(release_name):
    msg = 'Checking predb.me for "{release_name}"'
    logging.debug(msg.format(release_name=release_name))
    params = {
        'search': release_name,
        'cats': 'movies,-movies-discs',
    }
    try:
        response = requests.get('http://predb.me/', params=params)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        matches = set(link.text.strip() for link in soup.find_all('a', class_='p-title'))
        return release_name in matches
    except Exception as e:
        logging.warning(e)
        return False
