import json
import mimetypes
import os
import random
import shutil
import sys
import time
import uuid
from gettext import gettext as _
from io import BytesIO

from kivy.logger import Logger

from . import (DEFAULT_TILES_URL, DEFAULT_TILES_SUBDOMAINS,
               DEFAULT_TMP_DIR, DEFAULT_FILEPATH, DEFAULT_TILE_SIZE,
               DEFAULT_TILE_FORMAT, DEFAULT_TILE_SCHEME, DEFAULT_TIMEOUT,
               DEFAULT_DOWNLOAD_RETRIES, MAX_DOWNLOAD_TIME)
from .cache import Disk, Dummy
from .exceptions import EmptyCoverageError
from .mbutil import disk_to_mbtiles
from .proj import GoogleProjection
from .sources import TileDownloader, MBTilesReader
from .utils import tile_to_latlon

has_pil = False
try:
    import Image
    import ImageEnhance
    has_pil = True
except ImportError:
    try:
        from PIL import Image, ImageEnhance
        has_pil = True
    except ImportError:
        pass


class TilesManager(object):

    def __init__(self, **kwargs):
        """
        Manipulates tiles in general. Gives ability to list required tiles on a
        bounding box, download them, render them, extract them from other mbtiles...

        Keyword arguments:
        cache -- use a local cache to share tiles between runs (default True)

        tiles_dir -- Local folder containing existing tiles if cache is
                     True, or where temporary tiles will be written otherwise
                     (default DEFAULT_TMP_DIR)

        tiles_url -- remote URL to download tiles (*default DEFAULT_TILES_URL*)
        timeout -- timeout between tiles downloading requests (default DEFAULT_TIMEOUT)
        tiles_headers -- HTTP headers to send (*default empty*)


        mbtiles_file -- A MBTiles file providing tiles (*to extract its tiles*)

        tile_size -- default tile size (default DEFAULT_TILE_SIZE)
        tile_format -- default tile format (default DEFAULT_TILE_FORMAT)
        tile_scheme -- default tile format (default DEFAULT_TILE_SCHEME)
        """
        self.tile_size = kwargs.get('tile_size', DEFAULT_TILE_SIZE)
        self.tile_format = kwargs.get('tile_format', DEFAULT_TILE_FORMAT)
        self.tile_scheme = kwargs.get('tile_scheme', DEFAULT_TILE_SCHEME)

        # Tiles Download
        self.tiles_url = kwargs.get('tiles_url', DEFAULT_TILES_URL)
        self.tiles_subdomains = kwargs.get('tiles_subdomains', DEFAULT_TILES_SUBDOMAINS)
        self.timeout = kwargs.get('timeout', DEFAULT_TIMEOUT)
        self.download_retries = kwargs.get('download_retries', DEFAULT_DOWNLOAD_RETRIES)
        self.tiles_headers = kwargs.get('tiles_headers')

        # MBTiles reading
        self.mbtiles_file = kwargs.get('mbtiles_file')

        if self.mbtiles_file:
            self.reader = MBTilesReader(self.mbtiles_file, self.tile_size)
        else:
            mimetype, encoding = mimetypes.guess_type(self.tiles_url)
            if mimetype and mimetype != self.tile_format:
                self.tile_format = mimetype
                Logger.info(_("Tile format set to %s") % self.tile_format)
            self.reader = TileDownloader(self.tiles_url,
                                         timeout=self.timeout,
                                         download_retries=self.download_retries,
                                         headers=self.tiles_headers,
                                         subdomains=self.tiles_subdomains,
                                         tilesize=self.tile_size)

        # Tile files extensions
        self._tile_extension = mimetypes.guess_extension(self.tile_format, strict=False)
        assert self._tile_extension, _("Unknown format %s") % self.tile_format
        if self._tile_extension in ('.jpe', '.jpg'):
            self._tile_extension = '.jpeg'

        # Cache
        tiles_dir = kwargs.get('tiles_dir', DEFAULT_TMP_DIR)
        if kwargs.get('cache', True):
            self.cache = Disk(self.reader.basename, tiles_dir, extension=self._tile_extension)
            if kwargs.get('cache_scheme'):
                self.cache.scheme = kwargs.get('cache_scheme')
        else:
            self.cache = Dummy(extension=self._tile_extension)

    def tileslist(self, bbox, zoomlevels):
        """
        Build the tiles list within the bottom-left/top-right bounding
        box (minx, miny, maxx, maxy) at the specified zoom levels.
        Return a list of tuples (z,x,y)
        """
        proj = GoogleProjection(self.tile_size, zoomlevels, self.tile_scheme)
        return proj.tileslist(bbox)

    def tile(self, z_x_y):
        """
        Return the tile (binary) content of the tile and seed the cache.
        """
        (z, x, y) = z_x_y
        Logger.debug(_("tile method called with %s") % ([z, x, y]))

        output = self.cache.read((z, x, y))
        if output is None:
            output = self.reader.tile(z, x, y)
            self.cache.save(output, (z, x, y))
        return output


class MBTilesBuilder(TilesManager):
    def __init__(self, **kwargs):
        """
        A MBTiles builder for a list of bounding boxes and zoom levels.

        filepath -- output MBTiles file (default DEFAULT_FILEPATH)
        tmp_dir -- temporary folder for gathering tiles (default DEFAULT_TMP_DIR/filepath)
        ignore_errors -- ignore download errors during MBTiles
        """
        super(MBTilesBuilder, self).__init__(**kwargs)
        self.filepath = kwargs.get('filepath', DEFAULT_FILEPATH)
        self.attribution = kwargs.get('attribution')
        self.use_attribution = kwargs.get('use_attribution', True)
        self.ignore_errors = kwargs.get('ignore_errors', False)
        basename, ext = os.path.splitext(os.path.basename(self.filepath))
        self.tmp_dir = kwargs.get('tmp_dir', DEFAULT_TMP_DIR)
        self.tmp_dir = os.path.join(self.tmp_dir, basename)
        self.tile_format = kwargs.get('tile_format', DEFAULT_TILE_FORMAT)

        self._bboxes = []
        self._fetched_tiles = 0
        self._total_tiles = 0
        self._tile_download_time_list = [self.timeout + 0.15]

    def tileslist_full(self):
        tileslist = set()
        for bbox, levels in self._bboxes:
            tileslist = tileslist.union(self.tileslist(bbox, levels))
        return tileslist

    def get_approximate_size_mb(self, bbox, zoomlevels, max_sample_count=20):
        tileslist = self.tileslist(bbox, zoomlevels)
        total_tiles = len(tileslist)
        if total_tiles:
            sample_count = min(max_sample_count, max(5, int(total_tiles / 200)))
            tileslist = random.sample(tileslist, min(total_tiles, sample_count))
            sizes_b = []
            for z_x_y in tileslist:
                content = self.tile(z_x_y, run_process=False)
                if content:
                    sizes_b.append(len(content))
            approximate_size_b = 0
            if sizes_b:
                approximate_size_b = sum(sizes_b) / len(sizes_b) * total_tiles
            return approximate_size_b / 1024 / 1024
        return 0

    def get_approximate_size_mb_full(self, max_sample_count=20):
        return sum([
            self.get_approximate_size_mb(bbox, levels, max_sample_count=max_sample_count)
            for bbox, levels in self._bboxes
        ])

    def calculate_average_download_time(self, tiles_num: int = None, reset=False):
        if tiles_num is None:
            total_tiles = self._total_tiles or len(self.tileslist_full())
            tiles_num = total_tiles - self._fetched_tiles
        tile_download_time_list = self._tile_download_time_list or [MAX_DOWNLOAD_TIME]
        tile_download_time = sum(tile_download_time_list) / len(tile_download_time_list)
        if reset:
            self._tile_download_time_list.clear()
        return min(tile_download_time * tiles_num, MAX_DOWNLOAD_TIME)

    def add_coverage(self, bbox, zoomlevels):
        """
        Add a coverage to be included in the resulting mbtiles file.
        """
        self._bboxes.append((bbox, zoomlevels))

    def set_coverage(self, bbox, zoomlevels):
        """
        Set the only coverage to be included in the resulting mbtiles file.
        """
        self._bboxes = [(bbox, zoomlevels)]

    def clear_coverage(self):
        """
        Set the only coverage to be included in the resulting mbtiles file.
        """
        self._bboxes = []

    @property
    def zoomlevels(self):
        """
        Return the list of covered zoom levels, in ascending order
        """
        zooms = set()
        for coverage in self._bboxes:
            for zoom in coverage[1]:
                zooms.add(zoom)
        return sorted(zooms)

    @property
    def bbox_bounds(self):
        """
        Return the bounding box of covered areas
        """
        return self._bboxes[0][0]  #TODO: merge all coverages

    def get_bounds(self, tiles_list = None):
        """
        Return the bounds of minimum zoom level
        """
        tiles_list = tiles_list or self.tileslist_full()
        minz = min([z for z,x,y in tiles_list])
        tiles_with_min_zoom = [tile for tile in tiles_list if tile[0] == minz]
        x_list = [x for z,x,y in tiles_with_min_zoom]
        y_list = [y for z, x, y in tiles_with_min_zoom]
        minx = min(x_list)
        maxx = max(x_list)
        miny = min(y_list)
        maxy = max(y_list)
        max_lat, min_lon = tile_to_latlon(x=minx, y=miny, zoom=minz)
        min_lat, max_lon = tile_to_latlon(x=maxx +1, y=maxy +1, zoom=minz)
        return min_lon, min_lat, max_lon, max_lat

    def tile(self, z_x_y, **kwargs):
        run_process = kwargs.get('run_process', True)
        try:
            start_time = time.time()
            result = super().tile(z_x_y)
            self._tile_download_time_list.append(time.time() - start_time)
            if run_process:
                self._fetched_tiles += 1
            return result
        except Exception as e:
            self._tile_download_time_list.append(MAX_DOWNLOAD_TIME)
            Logger.warning(e)
            if not self.ignore_errors:
                raise

    def run(self, force=False):
        try:
            self._run(force)
        finally:
            self._clean_run()

    def _run(self, force):
        """
        Build a MBTile file.

        force -- overwrite if MBTiles file already exists.
        """
        if os.path.exists(self.filepath):
            if force:
                Logger.warning(_("%s already exists and will be overwritten.") % self.filepath)
            else:
                # Already built, do not do anything.
                Logger.info(_("%s already exists. Nothing to do.") % self.filepath)
                return

        # Clean previous runs
        self._clean_run()

        # Compute list of tiles
        tileslist = self.tileslist_full()
        Logger.debug(_("%s tiles in total.") % len(tileslist))
        self._total_tiles = len(tileslist)
        if not self._total_tiles:
            raise EmptyCoverageError(_("No tiles are covered by bounding boxes : %s") % self._bboxes)
        Logger.debug(_("%s tiles to be packaged.") % self._total_tiles)

        # Go through whole list of tiles and gather them in tmp_dir
        for (z, x, y) in tileslist:
            self._gather((z, x, y))

        # Some metadata
        middlezoom = self.zoomlevels[len(self.zoomlevels) // 2]
        lat = self.bbox_bounds[1] + (self.bbox_bounds[3] - self.bbox_bounds[1])/2
        lon = self.bbox_bounds[0] + (self.bbox_bounds[2] - self.bbox_bounds[0])/2
        metadata = {}
        metadata['name'] = str(uuid.uuid4())
        metadata['format'] = self._tile_extension[1:]
        metadata['minzoom'] = self.zoomlevels[0]
        metadata['maxzoom'] = self.zoomlevels[-1]
        metadata['bounds'] = '%s,%s,%s,%s' % tuple(self.get_bounds())
        metadata['center'] = '%s,%s,%s' % (lon, lat, middlezoom)
        if self.attribution and self.use_attribution:
            metadata['attribution'] = self.attribution
        metadatafile = os.path.join(self.tmp_dir, 'metadata.json')
        with open(metadatafile, 'w') as output:
            json.dump(metadata, output)

        # Package it!
        Logger.info(_("Build MBTiles file '%s'.") % self.filepath)
        extension = self.tile_format.split("image/")[-1]

        temp_filepath = os.path.join(self.tmp_dir, 'tmp.mbtiles')
        disk_to_mbtiles(
            self.tmp_dir,
            temp_filepath,
            format=extension,
            scheme=self.cache.scheme,
        )

        overwritten = os.path.exists(self.filepath)
        shutil.move(temp_filepath, self.filepath)
        if overwritten:
            Logger.warning(_("%s was successfully overwritten.") % self.filepath)

    def _gather(self, z_x_y):
        (z, x, y) = z_x_y
        files_dir, tile_name = self.cache.tile_file((z, x, y))
        tmp_dir = os.path.join(self.tmp_dir, files_dir)
        if not os.path.isdir(tmp_dir):
            os.makedirs(tmp_dir)
        tilecontent = self.tile((z, x, y))
        tilepath = os.path.join(tmp_dir, tile_name)
        with open(tilepath, 'wb') as f:
            f.write(tilecontent)

    def _clean_run(self):
        self._clean_gather()
        self._fetched_tiles = 0
        self._total_tiles = 0

    def _clean_gather(self):
        Logger.debug(_("Clean-up %s") % self.tmp_dir)
        try:
            shutil.rmtree(self.tmp_dir)
            #Delete parent folder only if empty
            try:
                parent = os.path.dirname(self.tmp_dir)
                os.rmdir(parent)
                Logger.debug(_("Clean-up parent %s") % parent)
            except OSError:
                pass
        except OSError:
            pass
        try:
            os.remove("%s-journal" % self.filepath)  # created by mbutil
        except OSError as e:
            pass



class ImageExporter(TilesManager):
    def __init__(self, **kwargs):
        """
        Arrange the tiles and join them together to build a single big image.
        """
        super(ImageExporter, self).__init__(**kwargs)

    def grid_tiles(self, bbox, zoomlevel):
        """
        Return a grid of (x, y) tuples representing the juxtaposition
        of tiles on the specified ``bbox`` at the specified ``zoomlevel``.
        """
        tiles = self.tileslist(bbox, [zoomlevel])
        grid = {}
        for (z, x, y) in tiles:
            if not grid.get(y):
                grid[y] = []
            grid[y].append(x)
        sortedgrid = []
        for y in sorted(grid.keys(), reverse=self.tile_scheme == 'tms'):
            sortedgrid.append([(x, y) for x in sorted(grid[y])])
        return sortedgrid

    def export_image(self, bbox, zoomlevel, imagepath):
        """
        Writes to ``imagepath`` the tiles for the specified bounding box and zoomlevel.
        """
        assert has_pil, _("Cannot export image without python PIL")
        grid = self.grid_tiles(bbox, zoomlevel)
        width = len(grid[0])
        height = len(grid)
        widthpix = width * self.tile_size
        heightpix = height * self.tile_size

        result = Image.new("RGBA", (widthpix, heightpix))
        offset = (0, 0)
        for i, row in enumerate(grid):
            for j, (x, y) in enumerate(row):
                offset = (j * self.tile_size, i * self.tile_size)
                img = self._tile_image(self.tile((zoomlevel, x, y)))
                result.paste(img, offset)
        Logger.info(_("Save resulting image to '%s'") % imagepath)
        result.save(imagepath)

    def _tile_image(self, data):
        """
        Tile binary content as PIL Image.
        """
        image = Image.open(BytesIO(data))
        return image.convert('RGBA')
