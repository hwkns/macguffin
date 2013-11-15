MacGuffin
=========

Automated tools for handling Scene and P2P film releases -- gather and verify metadata, take
screenshots and upload them to an image host, create a .torrent file and upload it to a bittorrent tracker.


Requirements
------------

- Debian or Ubuntu
- Python 2.7, 3.2, or 3.3
- ffmpeg or avconv
- mktorrent
- mediainfo
- unrar
  - On Debian 7 and above, you may need to pull the .deb for unrar from the squeeze repo:
    http://packages.debian.org/squeeze/i386/unrar/download
- python:beautifulsoup4
- python:lxml
- python:requests


Installation
------------

- `sudo apt-get install unrar ffmpeg ffprobe mediainfo mktorrent python-pip`
- `sudo apt-get install python-dev libxml2-dev libxslt-dev python-libxml2 python-libxslt1`
- `sudo pip install beautifulsoup4`
- `sudo pip install lxml`
- `sudo pip install requests`
- Edit config.py with your details
  - If you don't already have an API key from [TMDB](http://www.themoviedb.org), just
    [sign up](https://www.themoviedb.org/account/signup) and request one from your
    [account page](https://www.themoviedb.org/account).


Usage
-----

- `/path/to/macguffin/auto_upload.py /path/to/Release.You.Want.To.Upload [/path/to/Another.Release ...]`
- `/path/to/macguffin/auto_upload.py *`
- Don't use sudo to run this script.  If you see "Permission denied" errors, add your user to the group that owns the
referenced directory and make sure it has group write permissions.
