from pathlib import Path

from kivy.logger import Logger
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import (
    StringProperty,
    ListProperty,
    NumericProperty,
    DictProperty,
    BooleanProperty,
    OptionProperty,
    AliasProperty,
)

from elevation import ElevationBuilderThreaded, MARGIN
from elevation.sources import DEFAULT_RANGE
from enums import MapContent
from mbtiles import (
    DEFAULT_TILES_SUBDOMAINS,
    DEFAULT_TILE_FORMAT,
    DEFAULT_CACHE_DIR,
    MAX_DOWNLOAD_TIME,
    DEFAULT_TIMEOUT,
    MBTilesBuilderThreaded,
)
from providers import BROWSER_USER_AGENT
from tools.binding_manager import BindingManager
from tools.quadkey_url import QuadKeyUrl
from tools.utils import check_filepath_valid, try_delete_directory


class MBTilesDbCache(EventDispatcher):
    url = StringProperty(None, allownone=True)
    bbox = ListProperty(None, allownone=True)
    zoom_from = NumericProperty(None, allownone=True)
    zoom_to = NumericProperty(None, allownone=True)
    subdomains = ListProperty(DEFAULT_TILES_SUBDOMAINS)
    tile_timeout = NumericProperty(DEFAULT_TIMEOUT)
    filepath = StringProperty(None, allownone=True)
    attribution = StringProperty(None, allownone=True)
    use_attribution = BooleanProperty(False)
    tile_format = StringProperty(DEFAULT_TILE_FORMAT)
    headers = DictProperty({"User-Agent": BROWSER_USER_AGENT})
    map_content = OptionProperty(options=MapContent.values(), defaultvalue=MapContent.MAP_WITH_ELEVATION)
    elevation_margin = StringProperty(MARGIN)

    cache = BooleanProperty(True)
    cache_dir = StringProperty(DEFAULT_CACHE_DIR)
    valid = BooleanProperty(False)
    filepath_valid = BooleanProperty(False)
    downloading = BooleanProperty(False)

    _approximate_size_mb_map = NumericProperty(0)
    _approximate_size_mb_elevation = NumericProperty(0)
    approximate_size_mb = AliasProperty(
        getter=lambda self: round(
            (self._approximate_size_mb_map if self.map_content != MapContent.ONLY_ELEVATION else 0)
            + (self._approximate_size_mb_elevation if self.map_content != MapContent.ONLY_MAP else 0),
            2,
        ),
        cache=True,
        bind=['_approximate_size_mb_map', '_approximate_size_mb_elevation', 'map_content'],
    )
    approximate_size_max_sample_count = NumericProperty(20)
    time_to_download = NumericProperty(0)
    time_to_download_averaging_period_s = NumericProperty(2)
    _progress_map = ListProperty([0, 0])
    _progress_elevation = ListProperty([0, 0])
    progress = AliasProperty(
        getter=lambda self: [
            self._progress_map[0] + self._progress_elevation[0],
            self._progress_map[1] + self._progress_elevation[1],
        ],
        cache=True,
        bind=['_progress_map', '_progress_elevation'],
    )
    _success_map = BooleanProperty(False)
    _success_elevation = BooleanProperty(False)
    _success = AliasProperty(
        getter=lambda self: (
            (self._success_map if self.map_content != MapContent.ONLY_ELEVATION else True)
            and (self._success_elevation if self.map_content != MapContent.ONLY_MAP else True)
        ),
        cache=True,
        bind=['_success_map', '_success_elevation', 'map_content'],
    )
    _finish_map = BooleanProperty(False)
    _finish_elevation = BooleanProperty(False)
    _finish = AliasProperty(
        getter=lambda self: (
            (self._finish_map if self.map_content != MapContent.ONLY_ELEVATION else True)
            and (self._finish_elevation if self.map_content != MapContent.ONLY_MAP else True)
        ),
        cache=True,
        bind=['_finish_map', '_finish_elevation', 'map_content'],
    )
    __events__ = ['on_success', 'on_error', 'on_connection_lost', 'on_finish']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bindings = BindingManager()
        self._builder = self._create_builder()
        self.elevation_builder = self._create_elevation_builder()

        self._trigger_update_time_to_download = Clock.create_trigger(
            self._update_time_to_download, timeout=self.time_to_download_averaging_period_s
        )
        self._trigger_update_approximate_size = Clock.create_trigger(self._update_approximate_size, timeout=1)
        self._trigger_handle_input_change = Clock.create_trigger(self._handle_input_change)
        self._trigger_update_valid = Clock.create_trigger(self._update_valid)
        self.bind(map_content=self._reset_progress)
        self.bind(
            url=self._trigger_handle_input_change,
            bbox=self._trigger_handle_input_change,
            zoom_from=self._trigger_handle_input_change,
            zoom_to=self._trigger_handle_input_change,
            subdomains=self._trigger_handle_input_change,
            headers=self._trigger_handle_input_change,
            tile_format=self._trigger_handle_input_change,
            map_content=self._trigger_handle_input_change,
        )
        self.bind(
            url=self._trigger_update_valid,
            bbox=self._trigger_update_valid,
            zoom_from=self._trigger_update_valid,
            zoom_to=self._trigger_update_valid,
            filepath=self._trigger_update_valid,
            map_content=self._trigger_update_valid,
        )
        self.bind(
            approximate_size_mb=self._handle_approximate_size_mb,
            progress=Clock.create_trigger(self._handle_progress),
            _success=Clock.create_trigger(self._handle_success, 0.05),
            _finish=Clock.create_trigger(self._handle_finish, 0.05),
        )
        self._trigger_handle_input_change()
        self._trigger_update_valid()

    def _create_elevation_builder(self):
        builder = ElevationBuilderThreaded(
            progress_cb=lambda downloaded, total: setattr(self, '_progress_elevation', [downloaded, total]),
            error_cb=Clock.create_trigger(lambda *_: self.dispatch('on_error')),
            connection_lost_cb=Clock.create_trigger(lambda *_: self.dispatch('on_connection_lost')),
        )
        return builder

    @property
    def builder(self):
        builder = self._builder
        if not builder or (
            not self.downloading
            and (
                builder.tiles_url != self.url
                or builder.tiles_subdomains != self.subdomains
                or builder.tiles_headers != self.headers
                or builder.tile_format != self.tile_format
                or builder.timeout != self.tile_timeout
            )
        ):
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
            progress_cb=lambda downloaded, total: setattr(self, '_progress_map', [downloaded, total]),
            success_cb=Clock.create_trigger(lambda *_: setattr(self, '_success_map', True)),
            error_cb=Clock.create_trigger(lambda *_: self.dispatch('on_error')),
            connection_lost_cb=Clock.create_trigger(lambda *_: self.dispatch('on_connection_lost')),
            final_cb=Clock.create_trigger(lambda *_: setattr(self, '_finish_map', True)),
        )
        trigger_update_coverage = Clock.create_trigger(lambda *_: self._update_coverage(builder))
        self._bindings.bind_item(self, 'filepath', lambda i, v: setattr(builder, 'filepath', v))
        self._bindings.bind_item(self, 'attribution', lambda i, v: setattr(builder, 'attribution', v))
        self._bindings.bind_item(self, 'headers', lambda i, v: setattr(builder, 'tiles_headers', v))
        self._bindings.bind_item(self, 'tile_format', lambda i, v: setattr(builder, 'tile_format', v))
        self._bindings.bind_item(self, 'bbox', lambda i, v: trigger_update_coverage())
        self._bindings.bind_item(self, 'zoom_from', lambda i, v: trigger_update_coverage())
        self._bindings.bind_item(self, 'zoom_to', lambda i, v: trigger_update_coverage())
        self._update_coverage(builder)
        return builder

    def _update_coverage(self, builder):
        if None in (self.bbox, self.zoom_from, self.zoom_to):
            builder.clear_coverage()
        else:
            builder.set_coverage(
                bbox=(self.bbox[1], self.bbox[0], self.bbox[3], self.bbox[2]),
                zoomlevels=list(range(self.zoom_from, self.zoom_to + 1)),
            )

    def _handle_input_change(self, *_):
        self._approximate_size_mb_map = 0
        self._approximate_size_mb_elevation = 0
        self.time_to_download = 0
        self._trigger_update_approximate_size()

    def _handle_approximate_size_mb(self, *_):
        if self.approximate_size_mb:
            self._trigger_update_time_to_download()

    def _update_approximate_size(self, *_):
        if self.map_content != MapContent.ONLY_MAP:
            if self.bbox:
                self.elevation_builder.get_approximate_size_mb(
                    self.bbox,
                    margin=self.elevation_margin,
                    setter_cb=lambda size: setattr(self, '_approximate_size_mb_elevation', size),
                )
        if self.map_content != MapContent.ONLY_ELEVATION:
            if not None in (self.zoom_from, self.zoom_to) and self.url:
                self.builder.get_approximate_size_mb_full(
                    max_sample_count=self.approximate_size_max_sample_count,
                    setter_cb=lambda size: setattr(self, '_approximate_size_mb_map', size),
                )

    def _update_time_to_download(self, *_):
        if self.elevation_builder.is_running and not self.builder.is_running:
            mbtiles_time_to_download = 0
        else:
            mbtiles_time_to_download = (
                self.builder.calculate_average_download_time(
                    reset=self.builder.is_running or self.time_to_download >= MAX_DOWNLOAD_TIME
                )
                if self.map_content != MapContent.ONLY_ELEVATION
                else 0
            )
        elevation_time_to_download = (
            self.elevation_builder.calculate_average_time(self.bbox, margin=self.elevation_margin)
            if self.map_content != MapContent.ONLY_MAP
            else 0
        )

        self.time_to_download = mbtiles_time_to_download + elevation_time_to_download

    def _update_valid(self, *_):
        self.filepath_valid = bool(
            self.filepath
            and check_filepath_valid(self.filepath)
            and (filepath := Path(self.filepath)).name.replace('.mbtiles', '').replace('.tif', '')
            and filepath.parent.exists()
            and not '\\' in filepath.name
            and not '/' in filepath.name
        )
        self.valid = bool(
            self.filepath_valid
            and self.bbox is not None
            and (
                self.map_content == MapContent.ONLY_ELEVATION
                or (not None in (self.zoom_from, self.zoom_to) and self.url)
            )
            and (
                self.map_content == MapContent.ONLY_MAP
                or (self.bbox[0] >= DEFAULT_RANGE[0] and self.bbox[2] <= DEFAULT_RANGE[1])
            )
        )

    def _handle_progress(self, *_):
        self._trigger_update_time_to_download()
        if self.approximate_size_mb == 0:
            self._trigger_update_approximate_size()

    def _handle_success(self, *_):
        if self._success:
            self._merge_elevation_or_create_file_if_needed()

    def _merge_elevation_or_create_file_if_needed(self):
        trigger_set_finish_elevation = Clock.create_trigger(lambda *args: setattr(self, '_finish_elevation', True))
        trigger_dispatch_on_success = Clock.create_trigger(lambda *args: self.dispatch('on_success'))
        if self.map_content == MapContent.MAP_WITH_ELEVATION:
            self._finish_elevation = False
            self.elevation_builder.merge_threaded(
                self.bbox,
                self.filepath,
                max_zoom=self.zoom_to,
                margin=self.elevation_margin,
                success_cb=trigger_dispatch_on_success,
                final_cb=trigger_set_finish_elevation,
            )
        elif self.map_content == MapContent.ONLY_ELEVATION:
            self._finish_elevation = False
            self.elevation_builder.clip_threaded(
                self.bbox,
                output=self.filepath,
                margin=self.elevation_margin,
                success_cb=trigger_dispatch_on_success,
                final_cb=trigger_set_finish_elevation,
            )
        else:
            self.dispatch('on_success')

    def _handle_finish(self, *_):
        if self._finish:
            self.dispatch('on_finish')

    def _reset_progress(self, *args):
        self._progress_map = [0, 0]
        self._progress_elevation = [0, 0]
        self._success_map = False
        self._success_elevation = False
        self._finish_map = False
        self._finish_elevation = False

    def download(self, rewrite=False):
        if self.valid:
            Logger.info('Downloading started')
            self.downloading = True
            self._reset_progress()
            if self.map_content != MapContent.ONLY_ELEVATION:
                self.builder.run(rewrite)
            if self.map_content != MapContent.ONLY_MAP:
                self.elevation_builder.ensure_tiles_threaded(
                    self.bbox,
                    margin=self.elevation_margin,
                    success_cb=Clock.create_trigger(lambda *args: setattr(self, '_success_elevation', True)),
                    final_cb=Clock.create_trigger(
                        lambda *args: setattr(self, '_finish_elevation', not self._success_elevation)
                    ),
                )
        else:
            Logger.info('Downloading skipped')
            self.dispatch('on_finish')

    def on_success(self, *_):
        pass

    def on_error(self, *_):
        Clock.schedule_once(lambda *_: self.stop(), 0.1)

    def on_connection_lost(self, *_):
        self.time_to_download = MAX_DOWNLOAD_TIME

    def on_finish(self, *_):
        self.downloading = False

    def pause(self):
        self.builder.pause()
        self.elevation_builder.pause()

    def resume(self):
        self.builder.resume()
        self.elevation_builder.resume()

    def stop(self):
        self.builder.stop()
        if self.elevation_builder.is_running:
            self.elevation_builder.stop()
        else:
            self._finish_elevation = True
        self._trigger_handle_input_change()

    def on_progress(self, *_):
        Logger.info(f'Progress: {self.progress[0]}/{self.progress[1]}')

    def on_approximate_size_mb(self, *_):
        Logger.info(f'Approximate size: {self.approximate_size_mb}')

    def on_time_to_download(self, *_):
        Logger.info(f'Time to download: {self.time_to_download}')

    def clear_cache(self):
        if self.cache:
            try_delete_directory(self.cache_dir)
