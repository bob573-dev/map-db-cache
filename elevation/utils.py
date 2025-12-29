import os
import sqlite3
from pathlib import Path
from typing import Optional

from PIL import Image, TiffTags

from . import MARGIN
from .sources import PRODUCTS_SPECS
import requests


def get_content_length(url: str, timeout=10) -> Optional[int]:
    try:
        response = requests.head(url, allow_redirects=True, timeout=timeout)
        length = response.headers.get("Content-Length")
        return int(length) if length is not None else None
    except Exception as e:
        print(f"HEAD request error: {e}")
        return None


def build_bounds(bounds, margin=MARGIN):
    bottom, left, top, right = bounds
    if isinstance(margin, str) and margin.endswith('%'):
        margin_percent = float(margin[:-1])
        margin_lon = (right - left) * margin_percent / 100
        margin_lat = (top - bottom) * margin_percent / 100
    else:
        margin_lon = margin_lat = float(margin)
    return bottom - margin_lat, left - margin_lon, top + margin_lat, right + margin_lon


def ensure_setup(cache_dir, product):
    datasource_root = os.path.join(cache_dir, product)
    spec = PRODUCTS_SPECS[product]
    _ensure_setup(datasource_root, product=product, **spec)
    return datasource_root, spec


def _ensure_setup(root, folders=(), **kwargs):
    created_folders = []
    for path in [root] + [os.path.join(root, p) for p in folders]:
        if not os.path.exists(path):
            os.makedirs(path)
            created_folders.append(path)
    return created_folders


def get_mbtiles_metadata(mbtiles: str) -> dict:
    try:
        with sqlite3.connect(mbtiles) as conn:
            result = {}
            try:
                cur = conn.cursor()
                result = dict(cur.execute("SELECT * FROM metadata"))
            except Exception:
                pass
        conn.close()
    except Exception:
        pass
    return result


def update_metadata_field(mbtiles: str, name, value):
    with sqlite3.connect(mbtiles) as con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO metadata (name, value)
            VALUES (?, ?)
            """,
            (name, value),
        )
    con.close()


def get_geotiff_resolution(path: Path):
    img = Image.open(path)
    tags = {TiffTags.TAGS.get(k, k): v for k, v in img.tag.items()}

    scaleX, scaleY, _ = tags.get("ModelPixelScaleTag")
    tie = tags.get("ModelTiepointTag")
    i, j, k, x0, y0, z0 = tie

    width, height = img.size
    xmin = x0
    ymax = y0
    xmax = x0 + scaleX * width
    ymin = y0 - scaleY * height

    scale = (scaleX, scaleY)
    bounds = (xmin, ymin, xmax, ymax)
    center = ((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2)

    return scale, bounds, center
