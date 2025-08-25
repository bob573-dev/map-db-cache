import shutil
from pathlib import Path

from kivy.logger import Logger
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import StringProperty, ListProperty, NumericProperty, DictProperty, BooleanProperty

from mbtiles import DEFAULT_TILES_SUBDOMAINS, DEFAULT_TILE_FORMAT, DEFAULT_CACHE_DIR, MAX_DOWNLOAD_TIME, DEFAULT_TIMEOUT
from mbtiles.tiles_threaded import MBTilesBuilderThreaded
from providers import BROWSER_USER_AGENT
from tools.binding_manager import BindingManager
from tools.quadkey_url import QuadKeyUrl


class MBTilesDbCache(EventDispatcher):
    url = StringProperty(None, allownone=True)
    bbox = ListProperty(None, allownone=True)
    zoom_from = NumericProperty(None, allownone=True)
    zoom_to = NumericProperty( None, allownone=True)
    subdomains = ListProperty(DEFAULT_TILES_SUBDOMAINS)
    tile_timeout = NumericProperty(DEFAULT_TIMEOUT)
    filepath = StringProperty(None, allownone=True)
    attribution = StringProperty(None, allownone=True)
    use_attribution = BooleanProperty(False)
    tile_format = StringProperty(DEFAULT_TILE_FORMAT)
    headers = DictProperty({"User-Agent": BROWSER_USER_AGENT})

    cache = BooleanProperty(True)
    cache_dir = StringProperty(DEFAULT_CACHE_DIR)
    valid = BooleanProperty(False)
    downloading = BooleanProperty(False)
    progress = ListProperty([0,0])
    approximate_size_mb = NumericProperty(0)
    approximate_size_max_sample_count = NumericProperty(20)
    time_to_download = NumericProperty(MAX_DOWNLOAD_TIME)
    time_to_download_averaging_period_s = NumericProperty(3)
    __events__ = ['on_success', 'on_error', 'on_connection_lost', 'on_finish']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bindings = BindingManager()
        self._builder = self._create_builder()

        self._trigger_update_time_to_download = Clock.create_trigger(
            self._update_time_to_download,
            timeout=self.time_to_download_averaging_period_s
        )
        self._trigger_update_approximate_size = Clock.create_trigger(
            self._update_approximate_size,
            timeout=1
        )
        self._trigger_handle_input_change = Clock.create_trigger(self._handle_input_change)
        self._trigger_update_valid = Clock.create_trigger(self._update_valid)
        self.bind(
            url=self._trigger_handle_input_change,
            bbox=self._trigger_handle_input_change,
            zoom_from=self._trigger_handle_input_change,
            zoom_to=self._trigger_handle_input_change,
            subdomains=self._trigger_handle_input_change,
            headers=self._trigger_handle_input_change,
            tile_format=self._trigger_handle_input_change,
        )
        self.bind(
            url=self._trigger_update_valid,
            bbox=self._trigger_update_valid,
            zoom_from=self._trigger_update_valid,
            zoom_to=self._trigger_update_valid,
            filepath=self._trigger_update_valid,
        )
        self.bind(
            approximate_size_mb=self._handle_approximate_size_mb
        )
        self._trigger_handle_input_change()
        self._trigger_update_valid()

    @property
    def builder(self):
        builder = self._builder
        if (not builder
            or (not self.downloading and (
                    builder.tiles_url != self.url
                    or builder.tiles_subdomains != self.subdomains
                    or builder.tiles_headers != self.headers
                    or builder.tile_format != self.tile_format
                    or builder.timeout != self.tile_timeout))):
            self._builder = self._create_builder()
        return self._builder

    def _create_builder(self):
        self._bindings.unbind_items()
        builder = MBTilesBuilderThreaded(
            cache=self.cache,
            tiles_dir=self.cache_dir,
            tiles_headers=self.headers,
            tiles_url=QuadKeyUrl.from_url(self.url),
            tiles_subdomains=self.subdomains,
            timeout=self.tile_timeout,
            tile_format=self.tile_format,
            filepath=self.filepath,
            attribution=self.attribution,
            use_attribution=self.use_attribution,
            progress_cb=self._progress_cb,
            success_cb=Clock.create_trigger(lambda *_: self.dispatch('on_success')),
            error_cb=Clock.create_trigger(lambda *_: self.dispatch('on_error')),
            connection_lost_cb=Clock.create_trigger(lambda *_: self.dispatch('on_connection_lost')),
            final_cb=Clock.create_trigger(lambda *_: self.dispatch('on_finish')),
        )
        trigger_update_coverage = Clock.create_trigger(lambda *_: self._update_coverage(builder))
        self._bindings.bind_item(self, 'filepath', lambda i,v: setattr(builder, 'filepath', v))
        self._bindings.bind_item(self, 'attribution', lambda i,v: setattr(builder, 'attribution', v))
        self._bindings.bind_item(self, 'headers', lambda i,v: setattr(builder, 'tiles_headers', v))
        self._bindings.bind_item(self, 'tile_format', lambda i,v: setattr(builder, 'tile_format', v))
        self._bindings.bind_item(self, 'bbox', lambda i,v: trigger_update_coverage())
        self._bindings.bind_item(self, 'zoom_from', lambda i,v: trigger_update_coverage())
        self._bindings.bind_item(self, 'zoom_to', lambda i,v: trigger_update_coverage())
        self._update_coverage(builder)
        return builder

    def _update_coverage(self, builder):
        if None in (self.bbox, self.zoom_from, self.zoom_to):
            builder.clear_coverage()
        else:
            builder.set_coverage(
                bbox=(self.bbox[1], self.bbox[0], self.bbox[3], self.bbox[2]),
                zoomlevels=list(range(self.zoom_from, self.zoom_to + 1))
            )

    def _handle_input_change(self, *_):
        self.approximate_size_mb = 0
        self.time_to_download = MAX_DOWNLOAD_TIME
        self._trigger_update_approximate_size()

    def _handle_approximate_size_mb(self, *_):
        if self.approximate_size_mb:
            self._trigger_update_time_to_download()

    def _update_approximate_size(self, *_):
        if not None in (self.bbox, self.zoom_from, self.zoom_to) and self.url:
            self.builder.get_approximate_size_mb_full(
                max_sample_count=self.approximate_size_max_sample_count,
                setter_cb=lambda size: setattr(self, 'approximate_size_mb', round(size, 2))
            )

    def _update_time_to_download(self, *_):
        self.time_to_download = self.builder.calculate_average_download_time(reset=True)

    def _update_valid(self, *_):
        if None in (self.bbox, self.zoom_from, self.zoom_to, self.filepath) or not self.url:
            self.valid = False
            return
        if not Path(self.filepath).parent.exists():
            self.valid = False
            return
        self.valid = True

    def download(self, rewrite = False):
        if self.valid:
            Logger.info('Download started')
            self.downloading = True
            self._progress_cb(0, 0)
            self.builder.run(rewrite)
        else:
            Logger.info('Download skipped')
            self.dispatch('on_finish')

    def _progress_cb(self, downloaded, total):
        self.progress = downloaded, total
        self._trigger_update_time_to_download()
        if self.approximate_size_mb == 0:
            self._trigger_update_approximate_size()

    def on_success(self, *_):
        pass

    def on_error(self, *_):
        pass

    def on_connection_lost(self, *_):
        self.time_to_download = MAX_DOWNLOAD_TIME

    def on_finish(self, *_):
        self.downloading = False

    def pause(self):
        self.builder.pause()

    def resume(self):
        self.builder.resume()

    def stop(self):
        self.builder.stop()
        self._trigger_handle_input_change()

    def on_progress(self, *_):
        Logger.info(f'Progress: {self.progress[0]}/{self.progress[1]}')

    def on_approximate_size_mb(self, *_):
        Logger.info(f'Approximate size: {self.approximate_size_mb}')

    def on_time_to_download(self, *_):
        Logger.info(f'Time to download: {self.time_to_download}')

    def clear_cache(self):
        if self.cache and Path(self.cache_dir).is_dir():
            shutil.rmtree(self.cache_dir)
