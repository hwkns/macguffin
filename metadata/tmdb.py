from __future__ import print_function, unicode_literals, division, absolute_import
import logging

import requests

import config


class TMDB(object):

    def __init__(self, tmdb_id=None, imdb_id=None, title=None, year=None):

        if not config.TMDB_API_KEY:
            raise TMDBError('You must specify your TMDB API key in config.py')

        self.id = tmdb_id
        self.imdb_id = imdb_id
        self.title = title
        self.year = year
        self.base_url = 'https://api.themoviedb.org/3'
        self.json = None
        self.valid_poster_sizes = None
        self.original_title = None
        self.description = None
        self.poster_base = None
        self.poster_path = None
        self.poster_size = None
        self.poster_url = None

        self.session = requests.session()

    def get_configuration(self):

        logging.debug('Getting TMDB configuration.')

        params = {
            'api_key': config.TMDB_API_KEY
        }

        url = self.base_url + '/configuration'
        response = self.session.get(url, params=params)
        response.raise_for_status()
        response = response.json()

        self.poster_base = response['images']['secure_base_url']
        self.valid_poster_sizes = response['images']['poster_sizes']

        logging.info('DISCLAIMER: This product uses the TMDb API, but is not endorsed or certified by TMDb.')

    def get_id_by_imdb(self, imdb_id):

        params = {
            'api_key': config.TMDB_API_KEY
        }

        msg = 'Searching TMDB using IMDb ID "{id}"'
        logging.debug(msg.format(id=imdb_id))

        url = self.base_url + '/movie/' + imdb_id
        response = self.session.get(url, params=params)
        response = response.json()

        if response.get('status_code') == 6:
            msg = 'TMDB could not find IMDb ID "{id}"'
            logging.error(msg.format(id=imdb_id))
        else:
            return response['id']

    def get_id_by_title(self, title, year=None):

        params = {
            'api_key': config.TMDB_API_KEY,
            'query': title
        }

        if year is not None:
            params['year'] = year

        msg = 'Searching TMDB using query "{title}" and year "{year}"'
        logging.debug(msg.format(title=title, year=year))

        url = self.base_url + '/search/movie'
        response = self.session.get(url, params=params)
        response = response.json()

        if response['total_results'] == 0:
            msg = 'TMDB could not find title "{title}"'
            logging.error(msg.format(title=title))
        else:
            return response['results'][0]['id']

    def get_metadata(self, poster_size='w500'):

        # Make sure we have configuration data
        if not self.poster_base:
            self.get_configuration()

        # Make sure the poster size is valid
        if poster_size in self.valid_poster_sizes:
            self.poster_size = poster_size
        else:
            msg = 'Poster size "{size}" is not one of {valid_sizes}.'
            raise TMDBError(msg.format(size=poster_size, valid_sizes=self.valid_poster_sizes))

        # Find the TMDB ID, or abort the upload
        if self.id is None and self.imdb_id is not None:
            self.id = self.get_id_by_imdb(self.imdb_id)
        if self.id is None and self.title is not None:
            self.id = self.get_id_by_title(self.title, self.year)
        if self.id is None:
            raise TMDBError('Film could not be found on TMDB!')

        params = {
            'api_key': config.TMDB_API_KEY
        }

        msg = 'Getting TMDB info using ID "{id}"'
        logging.debug(msg.format(id=self.id))

        url = self.base_url + '/movie/' + str(self.id)
        response = self.session.get(url, params=params)
        self.json = response.json()

        if self.json.get('status_code') == 6:
            msg = 'Invalid TMDB ID "{id}"'
            logging.error(msg.format(id=self.id))
        else:
            self.imdb_id = self.json['imdb_id']
            self.title = self.json['title']
            self.original_title = self.json['original_title']
            self.description = self.json['overview']
            self.poster_path = self.json['poster_path']
            if self.poster_path is not None:
                self.poster_url = self.poster_base + self.poster_size + self.poster_path
            msg = 'Title: {title}'
            logging.debug(msg.format(title=self.title))
            msg = 'Poster: {url}'
            logging.info(msg.format(url=self.poster_url))


class TMDBError(Exception):
    pass