import appdirs
from pathlib import Path

CACHE_DIR = appdirs.user_cache_dir('map-db-cache', 'bob')
DEFAULT_OUTPUT = 'out.tif'
MARGIN = '0%'
DEFAULT_MAX_DOWNLOAD_TILES = 9

CACHE = Path("cache")
SPOOL = Path("spool")

from .builder_threaded import *
