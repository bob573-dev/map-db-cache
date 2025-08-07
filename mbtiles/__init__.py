"""
package was copy-pasted from the 'landez' lib with changes
"""

import os
import tempfile

""" Default tiles URL """
DEFAULT_TILES_URL = "http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
""" Default tiles subdomains """
DEFAULT_TILES_SUBDOMAINS = list("abc")
""" Base temporary folder """
DEFAULT_TMP_DIR = os.path.join(tempfile.gettempdir(), 'landez')
""" Default output MBTiles file """
DEFAULT_FILEPATH = os.path.join(os.getcwd(), "tiles.mbtiles")
""" Default tile size in pixels (*useless* in remote rendering) """
DEFAULT_TILE_SIZE = 256
""" Default tile format (mime-type) """
DEFAULT_TILE_FORMAT = 'image/png'
DEFAULT_TILE_SCHEME = 'wmts'
""" Number of retries for remove tiles downloading """
DEFAULT_DOWNLOAD_RETRIES = 10
""" Timeout between tiles downloading requests """
DEFAULT_TIMEOUT = 0.25
""" Timeout between tiles downloading attempt if no connection """
DEFAULT_CONNECTION_MAX_TIMEOUT = 15
DEFAULT_CACHE_DIR = 'cached_tiles'
MAX_DOWNLOAD_TIME = 2678400  # 31 days in s


from .tiles import *
from .sources import *
