import shutil
import sqlite3
import os
import uuid

from kivy.logger import Logger


def merge_tif_with_mbtiles(
    bounds,
    tifffile_file,
    mbtiles_file,
    tiff_source=None,
    run_id=None,
    delete_tifffile: bool = False,
):
    min_lat, min_lon, max_lat, max_lon = bounds
    try:
        run_id = run_id or uuid.uuid4().hex
        temp_mbtiles_file = mbtiles_file + f'.{run_id}'
        shutil.copy2(mbtiles_file, temp_mbtiles_file)

        with open(tifffile_file, "rb") as f:
            blob_data = f.read()

        with sqlite3.connect(temp_mbtiles_file) as con:
            cur = con.cursor()
            cur.execute(
                """CREATE TABLE dem_tiles (
                    id INTEGER PRIMARY KEY,
                    min_lon REAL NOT NULL,
                    min_lat REAL NOT NULL,
                    max_lon REAL NOT NULL,
                    max_lat REAL NOT NULL,
                    format TEXT NOT NULL,   -- "tif"/"tiff"/"geotiff", "asc", "hgt", "vrt", "img"/"png"/"jpg", etc.
                    source TEXT,            -- "SRTM1", "Copernicus30", "ASTER", etc.
                    data BLOB NOT NULL
                );"""
            )
            cur.execute("""CREATE INDEX idx_dem_bounds ON dem_tiles(min_lat, max_lat, min_lon, max_lon);""")
            cur.execute(
                """INSERT INTO dem_tiles
                (min_lon, min_lat, max_lon, max_lat, format, source, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (min_lon, min_lat, max_lon, max_lat, "tif", tiff_source, blob_data),
            )
            cur.close()
        con.close()

        shutil.move(temp_mbtiles_file, mbtiles_file)
        if delete_tifffile:
            os.remove(tifffile_file)

    except Exception as e:
        Logger.error("Could not connect to database")
        Logger.exception(e)
        raise e
