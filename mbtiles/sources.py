import os
import sqlite3
import time
import requests

from kivy.logger import Logger

from gettext import gettext as _
from .exceptions import ExtractionError, InvalidFormatError, DownloadError

try:
    from urllib.parse import urlparse, urlencode
    from urllib.request import urlopen, Request
except ImportError:
    from urlparse import urlparse
    from urllib import urlencode
    from urllib2 import urlopen, Request

from .utils import flip_y
from . import DEFAULT_TILE_SIZE, DEFAULT_DOWNLOAD_RETRIES, DEFAULT_TIMEOUT


class TileSource(object):
    def __init__(self, tilesize=None):
        if tilesize is None:
            tilesize = DEFAULT_TILE_SIZE
        self.tilesize = tilesize
        self.basename = ''

    def tile(self, z, x, y):
        raise NotImplementedError

    def metadata(self):
        return dict()


class MBTilesReader(TileSource):
    def __init__(self, filename, tilesize=None):
        super(MBTilesReader, self).__init__(tilesize)
        self.filename = filename
        self.basename = os.path.basename(self.filename)
        self._con = None
        self._cur = None

    def _query(self, sql, *args):
        """ Executes the specified `sql` query and returns the cursor """
        if not self._con:
            Logger.debug(_("Open MBTiles file '%s'") % self.filename)
            self._con = sqlite3.connect(self.filename)
            self._cur = self._con.cursor()
        sql = ' '.join(sql.split())
        Logger.debug(_("Execute query '%s' %s") % (sql, args))
        try:
            self._cur.execute(sql, *args)
        except (sqlite3.OperationalError, sqlite3.DatabaseError)as e:
            raise InvalidFormatError(_("%s while reading %s") % (e, self.filename))
        return self._cur

    def metadata(self):
        rows = self._query('SELECT name, value FROM metadata')
        rows = [(row[0], row[1]) for row in rows]
        return dict(rows)

    def zoomlevels(self):
        rows = self._query('SELECT DISTINCT(zoom_level) FROM tiles ORDER BY zoom_level')
        return [int(row[0]) for row in rows]

    def tile(self, z, x, y):
        Logger.debug(_("Extract tile %s") % ((z, x, y),))
        tms_y = flip_y(int(y), int(z))
        rows = self._query('''SELECT tile_data FROM tiles
                              WHERE zoom_level=? AND tile_column=? AND tile_row=?;''', (z, x, tms_y))
        t = rows.fetchone()
        if not t:
            raise ExtractionError(_("Could not extract tile %s from %s") % ((z, x, y), self.filename))
        return t[0]


class TileDownloader(TileSource):
    def __init__(self, url, timeout=None, download_retries=None, headers=None, subdomains=None, tilesize=None):
        super(TileDownloader, self).__init__(tilesize)
        self.tiles_url = url
        if timeout is None:
            timeout = DEFAULT_TIMEOUT
        self.timeout = timeout
        if download_retries is None:
            download_retries = DEFAULT_DOWNLOAD_RETRIES
        self.download_retries = download_retries
        self.tiles_subdomains = subdomains or ['a', 'b', 'c']
        parsed = urlparse(self.tiles_url)
        self.basename = parsed.netloc+parsed.path
        self.headers = headers or {}

    def tile(self, z, x, y):
        """
        Download the specified tile from `tiles_url`
        """
        Logger.debug(_("Download tile %s") % ((z, x, y),))
        # Render each keyword in URL ({s}, {x}, {y}, {z}, {size} ... )
        size = self.tilesize
        s = self.tiles_subdomains[(x + y) % len(self.tiles_subdomains)]
        try:
            url = self.tiles_url.format(s=s, x=x, y=y, z=z, size=size)
        except KeyError as e:
            raise DownloadError(_("Unknown keyword %s in URL") % e)

        Logger.debug(_("Retrieve tile at %s") % url)
        r = self.download_retries
        sleeptime = 1
        while r >= 0:
            try:
                time.sleep(self.timeout)
                request = requests.get(url, headers=self.headers)
                if request.status_code == 200:
                    return request.content
                raise DownloadError(
                    _("Status code : %s, url : %s") % (request.status_code, url),
                    status_code=request.status_code
                )
            except (requests.exceptions.ConnectionError, DownloadError) as e:
                Logger.debug(_("Download error, retry (%s left). (%s)") % (r, e))
                r -= 1
                time.sleep(sleeptime)
                # progressivly sleep longer to wait for this tile
                if (sleeptime <= 10) and (r % 2 == 0):
                    sleeptime += 1  # increase wait
        raise DownloadError(_("Cannot download URL %s") % url)
