import os
from typing import Optional

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
