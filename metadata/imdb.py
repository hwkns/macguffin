from __future__ import print_function, unicode_literals, division, absolute_import
import re
import sys
import logging

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


class IMDb(object):
    """
    This class represents a film's IMDb.com information
    """

    def __init__(self, imdb_id):

        valid_id = IMDb.get_valid_id(imdb_id)

        if valid_id:
            self.id = valid_id
            self.int_id = int(self.id[2:])
            self.link = 'http://www.imdb.com/title/{id}/'.format(id=self.id)
        else:
            msg = 'No valid IMDb ID could be found in the string "{string}".'
            raise IMDbError(msg.format(string=imdb_id))

        self.title = None
        self.year = None
        self.genres = []
        self.aka_list = []
        self.description = None

    def __repr__(self):
        if self.title and self.year:
            format_str = '{title} ({year}) - {link}'
            return format_str.format(title=self.title, year=self.year, link=self.link)
        else:
            return self.link

    def __eq__(self, other):
        if other is None:
            return False
        else:
            return self.id == other.id

    def __hash__(self):
        return None

    def _fetch_page(self, page=''):
        """
        Get the specified IMDb page for this film, as a BeautifulSoup object
        """

        url = 'http://www.imdb.com/title/{id}/{page}'.format(id=self.id, page=page)
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.RequestException as e:
            raise IMDbError(e)

        return BeautifulSoup(response.text)

    def get_metadata(self):
        """
        Fetch the title, year, genres, plot summary, and AKA titles from IMDb's web site
        """

        # Get description
        self.get_plotsummary_metadata()

        # Get title, year, and genres from the main page
        self.get_main_metadata()

        # Get the list of AKA titles
        self.get_aka_list()

    def get_main_metadata(self):

        dom = self._fetch_page()

        # Get genres
        subtext_div = dom.find('div', class_='subtext')
        self.genres = [span.string.strip() for span in subtext_div.find_all('span', itemprop='genre')]
        msg = 'Genre(s): {genres}'
        logging.info(msg.format(genres=', '.join(self.genres)))

        # Get title
        title_h1 = dom.find('h1', itemprop='name')
        self.title = next(title_h1.children).strip()
        msg = 'Title: {title}'
        logging.debug(msg.format(title=self.title))

        # Get year
        year_span = dom.find('span', id='titleYear')
        year_link = year_span.find('a')
        self.year = year_link.string.strip()
        msg = 'Year: {year}'
        logging.debug(msg.format(year=self.year))

        # Get description
        if self.description is None:
            description_div = dom.find(class_='summary_text', itemprop='description')
            if description_div is not None:
                description_div.string.strip()

    def get_plotsummary_metadata(self):

        dom = self._fetch_page('plotsummary')

        description_p = dom.find('p', class_='plotSummary')
        if description_p:
            self.description = next(description_p.children).strip()
            msg = 'Description: {description}'
            logging.info(msg.format(description=self.description))
        else:
            logging.debug('No plot summary found on IMDb')

    def get_aka_list(self):

        dom = self._fetch_page('releaseinfo')

        aka_table = dom.find('table', id='akas')

        if aka_table is None:
            return []

        rows = aka_table.find_all('tr')
        for row in rows:
            aka_title = row.find_all('td')[1].text.strip()
            self.aka_list.append(aka_title)
        msg = 'AKA titles: {titles}'
        logging.debug(msg.format(titles=self.aka_list))

    @staticmethod
    def get_valid_id(imdb_string):
        """
        Check the string for an IMDb ID, and format it as 'tt' + 7-digit number
        """
        if not imdb_string:
            return
        match = re.findall(r'tt(\d+)', imdb_string, re.IGNORECASE)
        if match:
            id_num = match[0]
            if len(id_num) < 7:
                # Pad id to 7 digits
                id_num = id_num.zfill(7)
            return 'tt' + id_num


class IMDbError(Exception):
    pass