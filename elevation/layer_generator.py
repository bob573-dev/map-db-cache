import colorsys
import math
import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from kivy.logger import Logger

import numpy as np
from PIL import Image
from pyproj import CRS
from pyproj import Geod

from elevation.utils import get_geotiff_resolution, get_mbtiles_metadata, update_metadata_field
from gdal_runner import GDALRunner
from mbtiles.mbutil import disk_to_mbtiles, prepare_metadata

from utils import is_win_platform


@dataclass
class LayerGenerator:
    @classmethod
    def generate_layer(
        cls,
        dem_tif: str,
        out_mbtiles: str,
        max_zoom=14,
    ):
        max_zoom = min(max_zoom, 14)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            temp_mbtiles = tmp / "temp.mbtiles"
            temp_tif = tmp / "temp.tif"
            color_file = tmp / "colors.txt"
            shutil.copy2(dem_tif, temp_tif)

            min_h, max_h = cls.get_elevation_range(dem_tif)
            land_h = max(max_h, 0) - max(min_h, 0)
            ramp = cls.generate_gdal_color_ramp(
                min_h=min_h,
                max_h=max_h,
            )
            with open(color_file, "w") as f:
                f.write(ramp)

            for zoom in range(max_zoom + 1):
                tiles_path = cls.generate_tiles_for_zoom(temp_tif, color_file, zoom, land_h)

            prepare_metadata(tiles_path, 0, max_zoom, (-180, -90, 180, 90))
            disk_to_mbtiles(
                tiles_path,
                temp_mbtiles,
            )

            shutil.move(temp_mbtiles, out_mbtiles)
            return out_mbtiles

    @staticmethod
    def get_elevation_range(tiff_path: str, nodata: int | float | None = -32768) -> tuple[float, float]:
        with Image.open(tiff_path) as img:
            data = np.array(img)

        data = data.astype(np.float32)

        if nodata is not None:
            data = data[data != nodata]

        data = data[~np.isnan(data)]

        if data.size == 0:
            raise ValueError("TIFF contains only NoData values")

        return float(data.min()), float(data.max())

    @classmethod
    def generate_gdal_color_ramp(
        cls,
        min_h: float,
        max_h: float,
        min_mountain_elevation: float = 400,
        max_peak_percent: float = 0.3,
    ) -> str:
        if max_h < min_h:
            raise ValueError("max_h must be >= min_h")
        if min_mountain_elevation <= 0:
            raise ValueError("min_mountain_elevation must be > 0")
        if max_peak_percent < 0:
            raise ValueError("max_peak_percent must be >= 0")

        lines = []
        lines.append("nv 0 0 0 0")

        lines += cls._generate_sea_lines(min_h)
        min_delta_land = 70
        min_land_h = max(min_h, 0)
        land_delta_h = math.ceil(max_h - min_land_h)
        if land_delta_h > min_delta_land and min_mountain_elevation > min_delta_land:
            peak_range_percent = cls.reversed_f(
                land_delta_h - min_delta_land, max_y=min_mountain_elevation - min_delta_land
            )
            peak_range_percent = min(peak_range_percent, 1)
        else:
            peak_range_percent = 0

        peak_percent = peak_range_percent * max_peak_percent
        peak_h = cls.percentile(min_land_h, max_h, 1 - peak_percent)

        lines += cls._generate_land_lines(min_land_h, peak_h, min_delta_land)
        lines += cls._generate_peak_lines(peak_h, max_h, peak_range_percent)

        return "\n".join(lines)

    @staticmethod
    def reversed_f(y, max_y, k=math.e):
        return (y / max_y) ** (1 / k)

    @classmethod
    def _generate_sea_lines(
        cls,
        min_h: float,
        max_h: float = -1,
    ):
        max_h = min(max_h, -1)
        min_h = min(min_h, max_h)
        min_delta_h = 70
        delta_h = math.ceil(max_h - min_h)

        max_hue = 250
        delta_hue = 55 * min(delta_h / min_delta_h, 1)
        min_hue = int(max_hue - delta_hue)

        return [cls._rgb_iteration_from_hue(step, delta_h, min_h, max_h, min_hue, max_hue) for step in range(delta_h)]

    @classmethod
    def _generate_land_lines(
        cls,
        min_h: float,
        max_h: float,
        min_delta_h: float,
    ):
        min_h = max(min_h, 0)
        max_h = max(max_h, min_h)
        delta_h = math.ceil(max_h - min_h)

        max_hue = 180
        delta_hue = 180 * min(delta_h / min_delta_h, 1)
        min_hue = int(max_hue - delta_hue)

        return [cls._rgb_iteration_from_hue(step, delta_h, min_h, max_h, min_hue, max_hue) for step in range(delta_h)]

    @classmethod
    def _generate_peak_lines(
        cls,
        min_h: float,
        max_h: float,
        range_percent: float,
    ):
        min_h = max(min_h, 0)
        max_h = max(max_h, min_h)
        range_percent = max(min(range_percent, 1), 0)
        delta_h = math.ceil(max_h - min_h)

        max_saturation = 0.75
        delta_saturation = 0.75 * range_percent
        min_saturation = max_saturation - delta_saturation
        return [
            cls._rgb_iteration_from_saturation(step, delta_h, min_h, max_h, min_saturation, max_saturation)
            for step in range(delta_h)
        ]

    @staticmethod
    def _rgb_iteration_from_hue(
        step: int,
        steps: int,
        min_h: float,
        max_h: float,
        min_hue: int,
        max_hue: int,
    ) -> str:
        t = step / (steps - 1)
        height = min_h + t * (max_h - min_h)
        hue = (max_hue - (t * (max_hue - min_hue))) / 360
        r, g, b = colorsys.hsv_to_rgb(hue, 0.75, 1.0)
        return f"{height:.3f} {int(r * 255)} {int(g * 255)} {int(b * 255)}"

    @staticmethod
    def _rgb_iteration_from_saturation(
        step: int,
        steps: int,
        min_h: float,
        max_h: float,
        min_saturation: float,
        max_saturation: float,
    ) -> str:
        t = step / (steps - 1)
        height = min_h + t * (max_h - min_h)
        saturation = max_saturation - (t * (max_saturation - min_saturation))
        r, g, b = colorsys.hsv_to_rgb(0.0, saturation, 1.0)
        return f"{height:.3f} {int(r * 255)} {int(g * 255)} {int(b * 255)}"

    @staticmethod
    def percentile(min_value, max_value, percent):
        return (max_value - min_value) * percent + min_value

    @classmethod
    def scale_to_zoom(
        cls,
        src: str,
        zoom: int,
    ):
        if zoom > 16:  # todo: you can split src and upscale separately if you want
            raise ValueError('upscaling > 16 zoom level is restricted')
        src = Path(src)
        dst = src.with_suffix(f".contour_{zoom}.tif")
        if dst.exists():
            os.remove(dst)
        pixel_degree_size, bounds, center = get_geotiff_resolution(src)
        native_zoom = cls.get_geotiff_native_zoom(
            src,
            pixel_size_degree=pixel_degree_size,
            center_coords=center,
        )
        if zoom > native_zoom:
            dff = zoom - native_zoom
            scale = 2**dff
        elif zoom < native_zoom:
            dff = native_zoom - zoom
            scale = 1 / (2**dff)
        else:
            shutil.copy2(src, dst)
            return dst

        w, h = cls.get_raster_size(
            src
        )  # todo: this can be used to calculate the maximum scale that can be used without exceeding the number of pixels
        GDALRunner().run(
            [
                "gdalwarp",
                "-r",
                "cubic",
                "-ts",
                str(math.ceil(w * scale)),
                str(math.ceil(h * scale)),
                str(src),
                str(dst),
            ]
        )
        return dst

    @classmethod
    def generate_tiles_for_zoom(
        cls,
        tif_file: str,
        color_file: str,
        zoom: int,
        land_delta_h: float,
    ):
        tif_file = Path(tif_file)
        folder = tif_file.parent  # todo: use temp dir here
        colored_tif = folder / f"colored_{zoom}.tif"
        hillshade_tif = folder / f"hillshade_{zoom}.tif"
        final_tif = folder / f"final_{zoom}.tif"

        tif_file = cls.scale_to_zoom(tif_file, zoom + 1)

        GDALRunner().run(
            [
                "gdaldem",
                "color-relief",
                str(tif_file),
                str(color_file),
                str(colored_tif),
                "-nearest_color_entry",
                "-co",
                "TILED=YES",
                "-co",
                "COMPRESS=DEFLATE",
            ]
        )

        GDALRunner().run(
            [
                "gdaldem",
                "hillshade",
                str(tif_file),
                str(hillshade_tif),
                "-az",
                "315",
                "-alt",
                "45",
                "-compute_edges",
                "-co",
                "TILED=YES",
                "-co",
                "COMPRESS=DEFLATE",
            ]
        )

        GDALRunner().gdal_calc(
            [
                "gdal_calc.py",
                "-A",
                str(colored_tif),
                "-B",
                str(hillshade_tif),
                "--calc=A*(0.7+0.3*(B/255.0))",
                "--allBands=A",
                "--type=Byte",
                "--outfile",
                str(final_tif),
                "--co",
                "TILED=YES",
                "--co",
                "COMPRESS=DEFLATE",
            ]
        )

        if zoom in (13, 14) and not is_win_platform():
            contour_geojson = folder / f"contour_{zoom}.geojson"
            thick_geojson = folder / f"thick_contour_{zoom}.geojson"
            thick_geojson_buf = folder / f"thick_contour_buf_{zoom}.geojson"
            thick_tif = folder / f"thick_contour_{zoom}.tif"
            thin_geojson = folder / f"thin_contour_{zoom}.geojson"
            thin_geojson_buf = folder / f"thin_contour_buf_{zoom}.geojson"
            thin_tif = folder / f"thin_contour_{zoom}.tif"

            if land_delta_h >= 500:
                line_step = 200
            elif land_delta_h >= 250:
                line_step = 100
            elif land_delta_h >= 125:
                line_step = 50
            else:
                # todo: skip contour
                line_step = 50
            line_step_thin = line_step / 5

            GDALRunner().run(
                [
                    "gdal_contour",
                    "-a",
                    "elev",
                    "-i",
                    str(line_step_thin),
                    str(tif_file),
                    str(contour_geojson),
                ]
            )

            GDALRunner().run(
                [
                    "ogr2ogr",
                    str(thick_geojson),
                    str(contour_geojson),
                    "-where",
                    f"elev % {line_step} = 0",
                ]
            )

            GDALRunner().run(
                [
                    "ogr2ogr",
                    str(thin_geojson),
                    str(contour_geojson),
                    "-where",
                    f"elev % {line_step} != 0",
                ]
            )
            pixel_degree_size, bounds, center = get_geotiff_resolution(tif_file)
            thick_size = pixel_degree_size[0]
            thin_size = pixel_degree_size[0] / 1.2

            GDALRunner().run(
                [
                    "ogr2ogr",
                    str(thick_geojson_buf),
                    str(thick_geojson),
                    "-dialect",
                    "sqlite",
                    "-sql",
                    f"SELECT elev, ST_Buffer(geometry, {thick_size}) AS geometry FROM contour",
                ]
            )

            GDALRunner().run(
                [
                    "ogr2ogr",
                    str(thin_geojson_buf),
                    str(thin_geojson),
                    "-dialect",
                    "sqlite",
                    "-sql",
                    f"SELECT elev, ST_Buffer(geometry, {thin_size}) AS geometry FROM contour",
                ]
            )

            GDALRunner().run(
                [
                    "gdal_rasterize",
                    "-burn",
                    "255",
                    "-l",
                    "contour",
                    "-tr",
                    str(pixel_degree_size[0]),
                    str(pixel_degree_size[1]),
                    "-te",
                    str(bounds[0]),
                    str(bounds[1]),
                    str(bounds[2]),
                    str(bounds[3]),
                    "-ot",
                    "Byte",
                    "-of",
                    "GTiff",
                    str(thick_geojson_buf),
                    str(thick_tif),
                ]
            )

            GDALRunner().run(
                [
                    "gdal_rasterize",
                    "-burn",
                    "200",
                    "-l",
                    "contour",
                    "-tr",
                    str(pixel_degree_size[0]),
                    str(pixel_degree_size[1]),
                    "-te",
                    str(bounds[0]),
                    str(bounds[1]),
                    str(bounds[2]),
                    str(bounds[3]),
                    "-ot",
                    "Byte",
                    "-of",
                    "GTiff",
                    str(thin_geojson_buf),
                    str(thin_tif),
                ]
            )

            final_tif_temp = final_tif.parent / f'final_temp_{zoom}.tif'
            GDALRunner().gdal_calc(
                [
                    "gdal_calc.py",
                    "-A",
                    str(final_tif),
                    "-B",
                    str(thin_tif),
                    "-C",
                    str(thick_tif),
                    "--calc=where(C==255,35,where(B==200,60,A))",
                    "--allBands=A",
                    "--type=Byte",
                    "--outfile",
                    str(final_tif_temp),
                    "--co",
                    "TILED=YES",
                    "--co",
                    "COMPRESS=DEFLATE",
                ]
            )
            final_tif = final_tif_temp

        tiles_path = folder / "tiles"
        tiles_path.mkdir(exist_ok=True)

        GDALRunner().gdal2tiles(
            [
                "gdal2tiles.py",
                "-z",
                str(zoom),
                str(final_tif),
                str(tiles_path),
            ]
        )
        return tiles_path

    @classmethod
    def get_geotiff_native_zoom(cls, path: str, pixel_size_degree: tuple, center_coords: tuple = (50, 23)) -> int:
        lat, lon = center_coords

        size_in_m = cls.get_pixel_size_in_m(path, pixel_size_degree, center_coords)

        crs = CRS.from_epsg(3857)
        circumference_lat = 2 * math.pi * crs.get_geod().a * math.cos(math.radians(lat))

        native_zoom = math.ceil(math.log2(circumference_lat / (size_in_m[0] * 256)))
        return native_zoom

    @staticmethod
    def get_pixel_size_in_m(path: str, pixel_size_degree, center_coords):

        geod = Geod(ellps="WGS84")
        lat, lon = center_coords
        pixel_size_deg_lat, pixel_size_deg_lon = pixel_size_degree

        x0, y0 = lon, lat
        x1, y1 = lon + pixel_size_deg_lon, lat

        az12, az21, dist_x = geod.inv(x0, y0, x1, y1)

        x0, y0 = lon, lat
        x1, y1 = lon, lat + pixel_size_deg_lat
        az12, az21, dist_y = geod.inv(x0, y0, x1, y1)

        return (dist_x, dist_y)

    @staticmethod
    def get_raster_size(tif: Path) -> tuple[int, int]:
        with Image.open(tif) as img:
            return img.width, img.height

    @staticmethod
    def add_layer(
        target_mbtiles: str,
        layer_mbtiles: str,
        name: str = None,
        layer_source=None,
    ):
        try:
            temp_target_mbtiles = tempfile.NamedTemporaryFile(prefix='target_', suffix=".mbtiles", delete=False).name
            shutil.copy2(target_mbtiles, temp_target_mbtiles)
            temp_layer_mbtiles = tempfile.NamedTemporaryFile(prefix='layer_', suffix=".mbtiles", delete=False).name
            shutil.copy2(layer_mbtiles, temp_layer_mbtiles)

            bounds_str = get_mbtiles_metadata(target_mbtiles).get('bounds')
            bounds = list(map(float, bounds_str.split(",")))
            update_metadata_field(temp_layer_mbtiles, 'bounds', bounds_str)

            with open(temp_layer_mbtiles, "rb") as f:
                blob_data = f.read()

            with sqlite3.connect(temp_target_mbtiles) as con:
                cur = con.cursor()
                cur.execute(
                    """CREATE TABLE IF NOT EXISTS layers
                       (
                           id      INTEGER PRIMARY KEY,
                           name     TEXT,
                           min_lon REAL NOT NULL,
                           min_lat REAL NOT NULL,
                           max_lon REAL NOT NULL,
                           max_lat REAL NOT NULL,
                           source  TEXT,          -- "SRTM1", "Copernicus30", "ASTER", etc.
                           data    BLOB NOT NULL
                       );"""
                )
                cur.execute(
                    """INSERT INTO layers
                           (name, min_lon, min_lat, max_lon, max_lat, source, data)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (name, *bounds, layer_source, blob_data),
                )
                cur.close()
            con.close()

            shutil.move(temp_target_mbtiles, target_mbtiles)
            os.remove(temp_layer_mbtiles)

        except Exception as e:
            Logger.error("Could not connect to database")
            Logger.exception(e)
            raise e
