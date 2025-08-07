import threading
import time
from typing import Callable

from kivy.logger import Logger

from . import DEFAULT_CONNECTION_MAX_TIMEOUT
from .exceptions import StopException, DownloadError
from .tiles import MBTilesBuilder


class MBTilesBuilderThreaded(MBTilesBuilder):
    def __init__(
            self,
            progress_cb: Callable[[int, int], None] = None,
            success_cb: Callable[[], None] = None,
            error_cb: Callable[[], None] = None,
            connection_lost_cb: Callable[[], None] = None,
            final_cb: Callable[[], None] = None,
            wait_connection = True,
            **kwargs
    ):
        kwargs.setdefault('download_retries', 0)
        super().__init__(**kwargs)
        self._progress_cb = progress_cb
        self._success_cb = success_cb
        self._error_cb = error_cb
        self._connection_lost_cb = connection_lost_cb
        self._final_cb = final_cb
        self.wait_connection = wait_connection

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

    def get_approximate_size_mb_full(self, max_sample_count=5, **kwargs):
        setter_cb: Callable[[float], None] = kwargs.get('setter_cb')
        default_func = super().get_approximate_size_mb_full

        def target(_sample_count):
            try:
                if not self._is_running.is_set():
                    self._reset_events()
                result = default_func(_sample_count)
                if setter_cb:
                    setter_cb(result)
            except DownloadError:
                if setter_cb:
                    setter_cb(0)
            except StopException:
                pass

        threading.Thread(
            target=target,
            args=(max_sample_count,),
            name='map-db-cache. Counting mbtiles approximate size',
            daemon=True
        ).start()

    def tile(self, z_x_y, **kwargs):
        run_process = kwargs.get('run_process', True)
        sleeptime = 1
        while True:
            if run_process:
                self._resume_event.wait()
                if self._stop_event.is_set():
                    raise StopException
            try:
                result = super().tile(z_x_y, **kwargs)
                self._no_connection.clear()
                if run_process:
                    self._call_progress_cb()
                return result
            except DownloadError as exc:
                self._call_connection_lost_cb_once()
                if (
                        not self.wait_connection
                        or exc.status_code is not None
                        or not run_process
                ):
                    raise exc
            if sleeptime < DEFAULT_CONNECTION_MAX_TIMEOUT:
                sleeptime += 1
            for _ in range(sleeptime * 2):
                if self._stop_event.is_set():
                    raise StopException
                time.sleep(0.5)

    def run(self, force=False):
        if not self._is_running.is_set():
            default_func = super().run

            def target(_force):
                try:
                    self._is_running.set()
                    default_func(_force)
                    self._call_success_cb()
                except StopException:
                    Logger.info('Run process was stopped')
                except Exception as exc:
                    Logger.exception('Run process was interrupted by exception.', exc_info=exc)
                    self._call_error_cb()
                finally:
                    self._reset_events()
                    self._call_final_cb()

            threading.Thread(
                target=target,
                args=(force,),
                name='map-db-cache. Building mbtiles',
                daemon=True
            ).start()

    def _call_progress_cb(self):
        Logger.debug(f'progress {self._fetched_tiles}/{self._total_tiles}')
        if self._progress_cb:
            self._progress_cb(self._fetched_tiles, self._total_tiles)

    def _call_success_cb(self):
        Logger.debug(f'successfully finished run process')
        if self._success_cb:
            self._success_cb()

    def _call_error_cb(self):
        Logger.debug(f'error while run process')
        if self._error_cb:
            self._error_cb()

    def _call_connection_lost_cb_once(self):
        if not self._no_connection.is_set():
            self._no_connection.set()
            Logger.debug(f'lost connection')
            if self._connection_lost_cb:
                self._connection_lost_cb()

    def _call_final_cb(self):
        if self._final_cb:
            self._final_cb()

    def pause(self):
        Logger.info('Pause')
        self._resume_event.clear()

    def resume(self):
        Logger.info('Resume')
        self._resume_event.set()

    def stop(self):
        Logger.info('Stop')
        self._stop_event.set()
        self._resume_event.set()
