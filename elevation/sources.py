import collections
import math


def srtm1_tile_ilonlat(lon, lat):
    return int(math.floor(lon)), int(math.floor(lat))


def srtm3_tile_ilonlat(lon, lat):
    ilon, ilat = srtm1_tile_ilonlat(lon, lat)
    return (ilon + 180) // 5 + 1, (64 - ilat) // 5


def srtm1_tiles_names(bottom, left, top, right, tile_name_template='{slat}/{slat}{slon}.tif'):
    ileft, itop = srtm1_tile_ilonlat(left, top)
    iright, ibottom = srtm1_tile_ilonlat(right, bottom)
    # special case often used *integer* top and right to avoid downloading unneeded tiles
    if isinstance(top, int) or top.is_integer():
        itop -= 1
    if isinstance(right, int) or right.is_integer():
        iright -= 1
    for ilon in range(ileft, iright + 1):
        slon = '%s%03d' % ('E' if ilon >= 0 else 'W', abs(ilon))
        for ilat in range(ibottom, itop + 1):
            slat = '%s%02d' % ('N' if ilat >= 0 else 'S', abs(ilat))
            yield tile_name_template.format(**locals())


def srtm3_tiles_names(bottom, left, top, right, tile_template='srtm_{ilon:02d}_{ilat:02d}.tif'):
    ileft, itop = srtm3_tile_ilonlat(left, top)
    iright, ibottom = srtm3_tile_ilonlat(right, bottom)
    for ilon in range(ileft, iright + 1):
        for ilat in range(itop, ibottom + 1):
            yield tile_template.format(**locals())


def srtm_ellip_tiles_names(bottom, left, top, right, tile_name_template='{slat}{slon}_wgs84.tif'):
    ileft, itop = srtm1_tile_ilonlat(left, top)
    iright, ibottom = srtm1_tile_ilonlat(right, bottom)

    for ilon in range(ileft, iright + 1):
        slon = '%s%03d' % ('E' if ilon >= 0 else 'W', abs(ilon))
        for ilat in range(ibottom, itop + 1):
            slat = '%s%02d' % ('N' if ilat >= 0 else 'S', abs(ilat))
            subdir = 'North' if ilat >= 0 else 'South'
            north_subdir = 'North_30_60' if ilat >= 30 else 'North_0_29'
            fname = tile_name_template.format(**locals())

            if ilat >= 0:
                yield ("{subdir}/{north_subdir}/{fname}".format(**locals()))
            else:
                yield ("{subdir}/{fname}".format(**locals()))


SRTM1_ELLIP_SPEC = {
    'folders': ('spool', 'cache'),
    'datasource_url': 'https://opentopography.s3.sdsc.edu/raster/SRTM_GL1_Ellip/SRTM_GL1_Ellip_srtm',
    'tile_ext': '.tif',
    'compressed_pre_ext': '',
    'compressed_ext': '',
    'tile_names': srtm_ellip_tiles_names,
    'range': [-55, 59],  # todo: check
}

SRTM1_SPEC = {
    'folders': ('spool', 'cache'),
    'datasource_url': 'https://s3.amazonaws.com/elevation-tiles-prod/skadi',
    'tile_ext': '.hgt',
    'compressed_pre_ext': '.hgt',
    'compressed_ext': '.hgt.gz',
    'tile_names': srtm1_tiles_names,
    'range': [-55, 59],  # todo: check
}

SRTM3_SPEC = {
    'folders': ('spool', 'cache'),
    'datasource_url': 'https://srtm.csi.cgiar.org/wp-content/uploads/files/srtm_5x5/TIFF',
    'tile_ext': '.tif',
    'compressed_pre_ext': '',
    'compressed_ext': '.zip',
    'tile_names': srtm3_tiles_names,
    'range': [-55, 59],  # todo: check
}

PRODUCTS_SPECS = collections.OrderedDict(
    [
        ('SRTM1', SRTM1_SPEC),
        ('SRTM3', SRTM3_SPEC),
        ('SRTM1_ELLIP', SRTM1_ELLIP_SPEC),
    ]
)

PRODUCTS = list(PRODUCTS_SPECS)
DEFAULT_PRODUCT = PRODUCTS[0]
DEFAULT_RANGE = PRODUCTS_SPECS[DEFAULT_PRODUCT]['range']
