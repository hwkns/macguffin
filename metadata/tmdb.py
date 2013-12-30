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
        self.base_url = 'https://api.themoviedb.org/3/'
        self.json = None
        self.valid_poster_sizes = None
        self.original_title = None
        self.description = None
        self.poster_base = None
        self.poster_path = None
        self.poster_size = None
        self.poster_url = None
        self.disclaimer_was_shown = False

        self.session = requests.session()

    def __repr__(self):
        return self.__class__.__name__

    def request(self, path='', method='GET', params=None, data=None, files=None, verify=None, allow_redirects=True):
        url = self.base_url + path

        # Make sure we include the API key in each request
        params_with_key = {
            'api_key': config.TMDB_API_KEY,
        }
        if params is not None:
            params_with_key.update(params)

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params_with_key,
                data=data,
                files=files,
                verify=verify,
                allow_redirects=allow_redirects,
            )
            if response.status_code == 404:
                return dict()
            else:
                response.raise_for_status()
        except requests.RequestException as e:
            msg = 'Could not connect to {site}: {error}'
            raise TMDBError(msg.format(site=self, error=e))

        try:
            return response.json()
        except ValueError:
            msg = 'Response is not JSON!\n{response_text}'
            raise TMDBError(msg.format(response_text=response.text))

    def get_configuration(self):

        logging.debug('Getting TMDB configuration.')

        response = self.request('configuration')

        self.poster_base = response['images']['secure_base_url']
        self.valid_poster_sizes = response['images']['poster_sizes']

        if not self.disclaimer_was_shown:
            logging.info('DISCLAIMER: This product uses the TMDb API, but is not endorsed or certified by TMDb.')
            self.disclaimer_was_shown = True

    def get_id_by_imdb(self, imdb_id):

        msg = 'Searching {site} using IMDb ID "{id}"'
        logging.debug(msg.format(site=self, id=imdb_id))

        response = self.request('movie/' + imdb_id)

        if not response:
            msg = '{site} could not find film with IMDb ID "{id}"'
            raise TMDBError(msg.format(site=self, id=imdb_id))

        return response['id']

    def get_id_by_title(self, title, year=None):

        params = {
            'query': title
        }

        if year is not None:
            params['year'] = year

        msg = 'Searching TMDB using query "{title}" and year "{year}"'
        logging.debug(msg.format(title=title, year=year))

        response = self.request('search/movie', params=params)

        if response['total_results'] == 0:
            msg = 'Could not find film title "{title}"'
            raise TMDBError(msg.format(title=title))

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

        msg = 'Getting TMDB info using ID "{id}"'
        logging.debug(msg.format(id=self.id))

        self.json = self.request('movie/' + str(self.id))

        if not self.json:
            msg = 'Invalid TMDB ID "{id}"'
            raise TMDBError(msg.format(id=self.id))
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