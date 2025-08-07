from math import radians, log, tan, cos, pi, floor, atan, sinh


def flip_y(y, zoom):
    return (2**zoom-1) - y


def latlon_to_tile_xy(lat, lon, zoom, integer=False):
    """
    Returns tile indexes in XYZ scheme
    """
    n = 2 ** zoom
    x = n * (lon + 180) / 360
    lat_rad = radians(lat)
    y = n * (1 - log(tan(lat_rad) + 1 / cos(lat_rad)) / pi) / 2
    if integer:
        return floor(x), floor(y)
    return x, y


def tile_to_latlon(x, y ,zoom):
    """
    Returns (latitude, longitude) fot tile in XYZ scheme
    """
    n = 2 ** zoom
    lon = x / n * 360 - 180
    lat_rad = atan(sinh(pi * (1 - 2 * y / n)))
    lat = lat_rad * 180 / pi
    return lat, lon
