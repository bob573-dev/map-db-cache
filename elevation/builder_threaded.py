import gzip
import math
import os
import random
import shutil
import tempfile
import threading
import time
import uuid
import zipfile
from pathlib import Path
from typing import Callable

import requests
from kivy.logger import Logger
from kivy.clock import Clock

from mbtiles import DEFAULT_CONNECTION_MAX_TIMEOUT, MAX_DOWNLOAD_TIME
from mbtiles import DEFAULT_DOWNLOAD_RETRIES, DEFAULT_TIMEOUT
from mbtiles.exceptions import DownloadError
from mbtiles.exceptions import StopException
from . import DEFAULT_OUTPUT, MARGIN, DEFAULT_MAX_DOWNLOAD_TILES, SPOOL, CACHE
from .layer_generator import LayerGenerator
from .mbutil import merge_tif_with_mbtiles
from .sources import DEFAULT_PRODUCT, PRODUCTS_SPECS
from .utils import build_bounds, ensure_setup, get_content_length
from gdal_runner import GDALRunner
from consts import ELEVATION_CACHE_DIR


class ElevationBuilderThreaded:
    def __init__(
        self,
        progress_cb: Callable[[int, int], None] = None,
        error_cb: Callable[[], None] = None,
        connection_lost_cb: Callable[[], None] = None,
        wait_connection=True,
        generate_layer=False,
        max_zoom=14,
        **kwargs,
    ):
        self._progress_cb = progress_cb
        self._error_cb = error_cb
        self._connection_lost_cb = connection_lost_cb
        self.wait_connection = wait_connection
        if wait_connection:
            kwargs.setdefault('download_retries', 1)
        self.timeout = kwargs.get('timeout', DEFAULT_TIMEOUT)
        self.download_retries = kwargs.get('download_retries', DEFAULT_DOWNLOAD_RETRIES)
        self._chunk_size_bytes = 1024 * 64  # 64 KB
        self._default_one_tile_bytes = 4_300_000
        self._processing_coefficient = (
            10  # indicates how much tile processing is heavier for progress than chunk downloading
        )

        self._gdal_runner = GDALRunner()
        self._layer_generator = LayerGenerator()

        self._fetched_tiles_chunks = 0
        self._total_tiles_chunks = 0
        self._all_tiles_processed = False
        self._tiles_processed = 0
        self._total_tiles = 0

        self.generate_layer = generate_layer
        self.max_zoom = max_zoom
        self._layer_zooms_generated = 0
        self._layer_generation_progress_coefficient = 4  # TODO: it's mock for download_time calculation
        self._default_time_to_download_one_chunk = 0.3  # TODO: it's mock for download_time calculation
        self._default_process_time = 15  # TODO: it's mock for download_time calculation
        self._chunk_download_time_list = [self._default_time_to_download_one_chunk]

        self._resume_event = threading.Event()
        self._stop_event = threading.Event()
        self._is_running = threading.Event()
        self._no_connection = threading.Event()
        self._reset_events()

    def _reset_events(self):
        self._resume_event.set()
        self._stop_event.clear()
        self._is_running.clear()
        self._no_connection.clear()

    @property
    def is_running(self) -> bool:
        return self._is_running.is_set()

    def ensure_tiles(
        self,
        bounds,
        cache_dir=ELEVATION_CACHE_DIR,
        margin=MARGIN,
        product=DEFAULT_PRODUCT,
        max_download_tiles=DEFAULT_MAX_DOWNLOAD_TILES,
    ) -> None:
        datasource_root, spec = ensure_setup(cache_dir, product)
        bounds = build_bounds(bounds, margin=margin)
        ensure_tiles_names = list(spec['tile_names'](*bounds))
        self._total_tiles = len(ensure_tiles_names)

        # FIXME: emergency hack to enforce the no-bulk-download policy
        if len(ensure_tiles_names) > max_download_tiles:
            raise RuntimeError(
                f"Too many tiles: {len(ensure_tiles_names)}. "
                f"Please consult the providers' websites for how to bulk download tiles."
            )

        for tile_name in ensure_tiles_names:
            self.ensure_tile(str(Path(tile_name).with_suffix('')), datasource_root=datasource_root, **spec)

    def _download_tile(self, url, destination) -> None:
        r = self.download_retries
        sleeptime = 1
        while r >= 0:
            try:
                time.sleep(self.timeout)
                last_time = time.time()
                destination_tmp = destination.with_suffix(destination.suffix + ".temp")
                response = requests.get(url, stream=True)
                if response.status_code == 200:
                    Path(destination_tmp).parent.mkdir(parents=True, exist_ok=True)
                    try:
                        with open(destination_tmp, "wb") as f:
                            for chunk in response.iter_content(self._chunk_size_bytes):
                                if self._stop_event.is_set():
                                    raise StopException
                                now = time.time()
                                f.write(chunk)
                                chunk_time = now - last_time
                                last_time = now
                                if self._is_running.is_set():
                                    self._chunk_download_time_list.append(chunk_time)
                                    self._fetched_tiles_chunks += 1
                                    if self._resume_event.is_set():
                                        self._call_progress_cb()
                    except StopException:
                        if destination_tmp.exists():
                            os.remove(destination_tmp)
                        return
                    destination_tmp.rename(destination)
                    return
                raise DownloadError(
                    f"ElevationBuilder: Status code: {response.status_code}, url: {url}",
                    status_code=response.status_code,
                )
            except Exception as e:
                Logger.debug(f"ElevationBuilder: Download error, retry ({r} left). ({e})")
                r -= 1
                time.sleep(sleeptime)
                # progressively sleep longer to wait for this tile
                if (sleeptime <= 10) and (r % 2 == 0):
                    sleeptime += 1
        raise DownloadError("ElevationBuilder: Cannot download URL {url}")

    def clip(
        self,
        bounds,
        output=DEFAULT_OUTPUT,
        margin=MARGIN,
        **kwargs,
    ) -> None:
        """Clip the DEM to given bounds.

        :param bounds: Output bounds in 'bottom, left, top, right' order.
        :param output: Path to output file. Existing files will be overwritten.
        :param margin: Decimal degree margin added to the bounds. Use '%' for percent margin.
        """
        bounds = build_bounds(bounds, margin=margin)
        datasource_root = self._seed(bounds=bounds, **kwargs)
        self._do_clip(datasource_root, bounds, output, **kwargs)

    def _seed(
        self,
        bounds,
        cache_dir=ELEVATION_CACHE_DIR,
        product=DEFAULT_PRODUCT,
        max_download_tiles=DEFAULT_MAX_DOWNLOAD_TILES,
        **kwargs,
    ) -> str:
        """Seed the DEM to given bounds.

        :param cache_dir: Root of the DEM cache folder.
        :param product: DEM product choice.
        :param bounds: Output bounds in 'bottom, left, top, right' order.
        :param max_download_tiles: Maximum number of tiles to process.
        """
        datasource_root, spec = ensure_setup(cache_dir, product)
        ensure_tiles_names = list(spec['tile_names'](*bounds))
        # FIXME: emergency hack to enforce the no-bulk-download policy
        if len(ensure_tiles_names) > max_download_tiles:
            raise RuntimeError(
                "Too many tiles: %d. Please consult the providers' websites "
                "for how to bulk download tiles." % len(ensure_tiles_names)
            )

        self._build_vrt(datasource_root, ensure_tiles_names, product)
        return datasource_root

    def _build_vrt(
        self,
        datasource_root,
        tiles_names,
        product=DEFAULT_PRODUCT,
    ):
        datasource_root = Path(datasource_root)
        cache_dir = datasource_root / "cache"
        vrt_path = datasource_root / f"{product}.vrt"

        if not tiles_names:
            raise RuntimeError(f"No TIFF tiles provided. " f"Nothing to build VRT from.")

        tif_files = []
        for tile_name in tiles_names:
            file = cache_dir / tile_name
            if not file.is_file() or file.stat().st_size == 0:
                raise RuntimeError(f"TIFF tiles '{file}' is not file or is empty")
            tif_files.append(str(file))

        cmd = [
            "gdalbuildvrt",
            "-q",
            "-overwrite",
            str(vrt_path),
            *tif_files,
        ]
        self._gdal_runner.run(cmd)
        return vrt_path

    def _do_clip(
        self,
        path,
        bounds,
        output,
        product=DEFAULT_PRODUCT,
        **kwargs,
    ):
        run_id = uuid.uuid4().hex
        self._copy_vrt(path, product, run_id)
        self._clip_vrt(path=path, product=product, run_id=run_id, bounds=bounds, output=output)

    def _copy_vrt(self, path, product, run_id):
        path = Path(path)
        src = path / f"{product}.vrt"
        dst = path / f"{product}.{run_id}.vrt"

        if not src.exists():
            raise FileNotFoundError(f"Source VRT file not found: {src}")
        shutil.copy2(src, dst)
        return dst

    def _clip_vrt(self, path, product, run_id, bounds, output):
        path = Path(path)
        vrt_input = path / f"{product}.{run_id}.vrt"

        if not vrt_input.exists():
            raise FileNotFoundError(f"Input VRT not found: {vrt_input}")

        bottom, left, top, right = bounds
        projwin = [left, top, right, bottom]

        cmd = [
            "gdal_translate",
            "-q",
            "-co",
            "TILED=YES",
            "-co",
            "COMPRESS=DEFLATE",
            "-co",
            "ZLEVEL=9",
            "-co",
            "PREDICTOR=2",
            "-projwin",
            *map(str, projwin),  # projwin = (ulx, uly, lrx, lry)
            str(vrt_input),
            str(output),
        ]
        self._gdal_runner.run(cmd)

        rm_path = path / f"{product}.{run_id}.vrt"
        if rm_path.exists():
            os.remove(rm_path)

    def merge(
        self,
        bounds,
        mbtiles_file,
        product=DEFAULT_PRODUCT,
        margin=MARGIN,
        **kwargs,
    ) -> None:
        tifffile = tempfile.NamedTemporaryFile(suffix=".tif", delete=False).name
        self.clip(bounds, tifffile, margin, product=product, **kwargs)

        bounds = build_bounds(bounds, margin=margin)
        merge_tif_with_mbtiles(bounds, tifffile, mbtiles_file, tiff_source=product)

        if self.generate_layer:
            layer_mbtiles = tempfile.NamedTemporaryFile(suffix=".mbtiles", delete=False).name
            self._layer_generator.generate_layer(
                tifffile,
                layer_mbtiles,
                max_zoom=self.max_zoom,
                layer_zooms_generated_cb=self._layer_zooms_generated_cb,
            )

            self._layer_generator.add_layer(
                target_mbtiles=mbtiles_file, layer_mbtiles=layer_mbtiles, name='Terrain', layer_source=product
            )

        os.remove(tifffile)

    def _layer_zooms_generated_cb(self, zooms_generated):
        self._layer_zooms_generated = zooms_generated
        self._call_progress_cb()

    def get_tile_names(
        self,
        bounds,
        product=DEFAULT_PRODUCT,
        margin=MARGIN,
    ):
        spec = PRODUCTS_SPECS[product]
        bounds = build_bounds(bounds, margin=margin)
        return list(spec['tile_names'](*bounds))

    def _count_tiles(
        self,
        bounds,
        product=DEFAULT_PRODUCT,
        margin=MARGIN,
    ):
        tiles_names = self.get_tile_names(bounds, product, margin)
        spec = PRODUCTS_SPECS[product]
        result = 0
        self._total_tiles = len(tiles_names)

        for tile_name in tiles_names:
            tile = str(Path(tile_name).with_suffix('')).replace('\\', '/')
            url = f"{spec['datasource_url']}/{tile}{spec['compressed_ext']}"
            length = get_content_length(url)
            result += math.ceil(length / self._chunk_size_bytes)
        self._total_tiles_chunks = result

    def get_approximate_size_mb(
        self,
        bounds,
        setter_cb: Callable[[float], None] = None,
        product=DEFAULT_PRODUCT,
        margin=MARGIN,
    ):
        def target():
            try:
                if not self._is_running.is_set():
                    self._reset_events()
                self._count_tiles(bounds, product=product, margin=margin)
                if setter_cb:
                    if self.generate_layer:
                        bottom, left, top, right = bounds
                        one_lat_degree_in_km = 111.32
                        side_km = (top - bottom) * one_lat_degree_in_km
                        Clock.schedule_once(lambda *_: setter_cb(side_km * 1.9 * random.uniform(0.95, 1.05)))
                    else:
                        Clock.schedule_once(lambda *_: setter_cb(1 * random.uniform(0.51, 1)))
                return
            except DownloadError:
                if setter_cb:
                    Clock.schedule_once(lambda *_: setter_cb(0))
            except StopException:
                pass
            except Exception:
                self._chunk_download_time_list = [MAX_DOWNLOAD_TIME]

        threading.Thread(target=target, name='map-db-cache. Counting DEM approximate size', daemon=True).start()

    def calculate_average_time(
        self,
        bounds,
        product=DEFAULT_PRODUCT,
        margin=MARGIN,
    ):
        if not bounds:
            return 0

        total_tiles = self._total_tiles or len(self.get_tile_names(bounds, product, margin))
        total_tiles_chunks = (
            self._total_tiles_chunks or total_tiles * self._default_one_tile_bytes / self._chunk_size_bytes
        )

        download_tiles_chunks = total_tiles_chunks - self._fetched_tiles_chunks
        chunk_download_time_list = self._chunk_download_time_list or [0]
        chunk_download_time = sum(chunk_download_time_list) / len(chunk_download_time_list)
        download_time = download_tiles_chunks * (
            chunk_download_time or self._default_time_to_download_one_chunk * random.uniform(0.8, 1.2)
        )

        tiles_to_process = total_tiles - self._tiles_processed
        if not self._all_tiles_processed:
            tiles_to_process += 1

        processing_time = self._default_process_time * random.uniform(0.8, 1.2) * tiles_to_process
        if self.generate_layer and self.max_zoom is not None:
            total = min(self.max_zoom, self._layer_generator.PERMITTED_MAX_ZOOM) + 1
            processing_time += (
                total - self._layer_zooms_generated
            ) * self._layer_generation_progress_coefficient

        return max(download_time, 0) + max(processing_time, 0)

    def ensure_tile(self, *args, **kwargs):
        sleeptime = 1
        while True:
            self._resume_event.wait()
            if self._stop_event.is_set():
                raise StopException
            try:
                result = self._ensure_tile(*args, **kwargs)
                self._no_connection.clear()
                self._call_progress_cb()
                return result
            except DownloadError as exc:
                self._call_connection_lost_cb_once()
                if not self.wait_connection:
                    raise exc
            if sleeptime < DEFAULT_CONNECTION_MAX_TIMEOUT:
                sleeptime += 1
            for _ in range(sleeptime * 2):
                if self._stop_event.is_set():
                    raise StopException
                time.sleep(0.5)

    def _ensure_tile(
        self,
        tile_name,
        datasource_url,
        datasource_root,
        compressed_ext='',
        tile_ext='.tif',
        **kwargs,
    ):
        """
        spool/%compressed_ext:
        spool/%tile_ext
        cache/%.tif
        """
        tile_name = tile_name.replace('\\', '/')
        compressed_path = datasource_root / SPOOL / (tile_name + compressed_ext)
        raw_path = datasource_root / SPOOL / (tile_name + tile_ext)
        out_tif = datasource_root / CACHE / (tile_name + ".tif")

        if compressed_path.exists():
            self._fetched_tiles_chunks += math.ceil(compressed_path.stat().st_size / self._chunk_size_bytes)
        else:
            url = f"{datasource_url}/{tile_name}{compressed_ext}"
            self._download_tile(url, compressed_path)

        self._resume_event.wait()
        if self._stop_event.is_set():
            raise StopException

        if not raw_path.exists():
            if compressed_ext.endswith(".zip"):
                try:
                    with zipfile.ZipFile(compressed_path, "r") as z:
                        z.extract(tile_name + tile_ext, datasource_root / SPOOL)
                except:
                    raw_path.touch()  # fallback empty
            elif compressed_ext.endswith(".gz"):
                try:
                    with gzip.open(compressed_path, "rb") as f_in, open(raw_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                except:
                    raw_path.touch()

        self._resume_event.wait()
        if self._stop_event.is_set():
            raise StopException

        if not out_tif.exists() and raw_path.exists():
            out_tif.parent.mkdir(parents=True, exist_ok=True)
            cmd = [
                "gdal_translate",
                '-q',
                '-co',
                'TILED=YES',
                '-co',
                'COMPRESS=DEFLATE',
                '-co',
                'ZLEVEL=9',
                '-co',
                'PREDICTOR=2',
                str(raw_path),
                str(out_tif),
            ]
            self._gdal_runner.run(cmd)
        self._tiles_processed += 1

        return out_tif.exists()

    def ensure_tiles_threaded(
        self,
        bounds,
        product=DEFAULT_PRODUCT,
        margin=MARGIN,
        success_cb=None,
        final_cb=None,
    ) -> None:
        if not self._is_running.is_set():
            self._fetched_tiles_chunks = 0
            self._all_tiles_processed = False
            self._tiles_processed = 0
            self._layer_zooms_generated = 0

            self._chunk_download_time_list.clear()
            self._call_progress_cb()

            def target():
                try:
                    self._is_running.set()
                    try:
                        self.ensure_tiles(bounds=bounds, product=product, margin=margin)
                    except RuntimeError as exc:
                        Logger.exception(exc, exc_info=exc)
                        raise exc
                    self._call_success_cb(success_cb)
                except StopException:
                    self._clean_run()
                    Logger.info('ElevationBuilderThreaded: Downloading process was stopped')
                except Exception as exc:
                    Logger.exception(
                        'ElevationBuilderThreaded: Downloading process was interrupted by exception.', exc_info=exc
                    )
                    self._clean_run()
                    self._call_error_cb()
                finally:
                    self._reset_events()
                    self._call_final_cb(final_cb)

            threading.Thread(target=target, name='map-db-cache. Downloading DEM', daemon=True).start()

    def clip_threaded(
        self,
        *args,
        success_cb=None,
        final_cb=None,
        **kwargs,
    ) -> None:
        if not self._is_running.is_set():

            def target():
                try:
                    self._resume_event.wait()
                    if self._stop_event.is_set():
                        raise StopException
                    self._is_running.set()
                    self.clip(*args, **kwargs)
                    self._all_tiles_processed = True
                    self._call_progress_cb()
                    self._call_success_cb(success_cb)
                except StopException:
                    Logger.info('ElevationBuilderThreaded: Clip process was stopped')
                except Exception as exc:
                    Logger.exception('ElevationBuilderThreaded: Clip process was interrupted by exception.', exc_info=exc)
                    self._call_error_cb()
                finally:
                    self._clean_run()
                    self._reset_events()
                    self._call_final_cb(final_cb)

            threading.Thread(target=target, name='map-db-cache. Clip DEM', daemon=True).start()

    def _clean_run(self):
        self._fetched_tiles_chunks = 0
        self._total_tiles_chunks = 0
        self._all_tiles_processed = False
        self._tiles_processed = 0
        self._total_tiles = 0
        self._layer_zooms_generated = 0

    def merge_threaded(
        self,
        *args,
        success_cb=None,
        final_cb=None,
        **kwargs,
    ) -> None:
        if not self._is_running.is_set():

            def target():
                try:
                    self._resume_event.wait()
                    if self._stop_event.is_set():
                        raise StopException
                    self._is_running.set()
                    self.merge(*args, **kwargs)
                    self._all_tiles_processed = True
                    self._call_progress_cb()
                    self._call_success_cb(success_cb)
                except StopException:
                    Logger.info('ElevationBuilderThreaded: Merge process was stopped')
                except Exception as exc:
                    Logger.exception(
                        'ElevationBuilderThreaded: Merge process was interrupted by exception.', exc_info=exc
                    )
                    self._call_error_cb()
                finally:
                    self._clean_run()
                    self._reset_events()
                    self._call_final_cb(final_cb)

            threading.Thread(target=target, name='map-db-cache. Merge DEM with mbtiles', daemon=True).start()

    def _call_progress_cb(self):
        current = self._fetched_tiles_chunks + self._processing_coefficient * (
            int(self._all_tiles_processed) + self._tiles_processed
        )
        total = self._total_tiles_chunks + self._processing_coefficient * (1 + self._total_tiles)

        if self.generate_layer:
            current += self._layer_zooms_generated * self._layer_generation_progress_coefficient
            total += (min(self.max_zoom, self._layer_generator.PERMITTED_MAX_ZOOM) + 1) * self._layer_generation_progress_coefficient

        Logger.debug(f'ElevationBuilderThreaded: progress {current}/{total}')
        if self._progress_cb:
            self._progress_cb(current, total)

    def _call_success_cb(self, success_cb):
        Logger.debug(f'ElevationBuilderThreaded: successfully finished process')
        if success_cb:
            success_cb()

    def _call_error_cb(self):
        Logger.debug(f'ElevationBuilderThreaded: error while process')
        if self._error_cb:
            self._error_cb()

    def _call_connection_lost_cb_once(self):
        if not self._no_connection.is_set():
            self._no_connection.set()
            Logger.debug(f'ElevationBuilderThreaded: lost connection')
            if self._connection_lost_cb:
                self._connection_lost_cb()

    def _call_final_cb(self, final_cb=None):
        if final_cb:
            final_cb()

    def pause(self):
        Logger.info('ElevationBuilderThreaded: Pause')
        self._resume_event.clear()

    def resume(self):
        Logger.info('ElevationBuilderThreaded: Resume')
        self._resume_event.set()

    def stop(self):
        Logger.info('ElevationBuilderThreaded: Stop')
        self._stop_event.set()
        self._resume_event.set()


__all__ = ['ElevationBuilderThreaded']
