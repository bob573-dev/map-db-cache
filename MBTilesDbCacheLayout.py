import re
from pathlib import Path

from kivy.logger import Logger
from kivy.clock import Clock
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, ListProperty, DictProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.progressbar import ProgressBar
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.widget import Widget

from TextInputTitledLayout import TextInputTitledLayout
from FileChooser import FileChooserPopup
from MBTilesDbCache import MBTilesDbCache
from MapPanel import MapPanel
from TextInputRangedTitledLayout import TextInputRangedTitledLayout
from consts import DEFAULT_MIN_ZOOM, DEFAULT_MAX_ZOOM, DEFAULT_MAPS_DIRECTORY, CUSTOM_PROVIDER_KEY, FONT_SIZE_MEDIUM, \
    DROPDOWN_DOWN_PNG, DROPDOWN_UP_PNG, FOLDER_PNG, HEADER_BACKGROUND, HEADER_TEXT_COLOR, \
    DEFAULT_MAP_BASENAME
from mbtiles import DEFAULT_TILES_SUBDOMAINS, DEFAULT_TILE_FORMAT, MAX_DOWNLOAD_TIME, DEFAULT_TIMEOUT
from providers import PROVIDERS, BROWSER_USER_AGENT, DEFAULT_PROVIDER
from tools.utils import format_seconds
from uix import (
    InfoPopup, FileExistsPopup, LabelAutoresized, TextInputCoord,
    TextInputUnderlined, BoxLayoutColored, ColoredLayout, BoxLayoutShort, SwitchButtonColored, ButtonColored,
    ProviderLabel, ButtonImage
)


class MBTilesDbCacheLayout(ColoredLayout, FloatLayout):
    provider = StringProperty(defaultvalue=DEFAULT_PROVIDER)
    provider_url = StringProperty()
    attribution = StringProperty()
    use_attribution = BooleanProperty(False)
    subdomains = ListProperty()
    headers = DictProperty({"User-Agent": BROWSER_USER_AGENT})
    tile_format = StringProperty(DEFAULT_TILE_FORMAT)
    tile_timeout = NumericProperty(DEFAULT_TIMEOUT)
    side = NumericProperty(defaultvalue=13, allownone=True)
    min_side = NumericProperty(1)
    max_side = NumericProperty(25)
    zoom = NumericProperty(defaultvalue=5)
    zoom_to = NumericProperty(16, allownone=True)
    min_zoom = NumericProperty(defaultvalue=DEFAULT_MIN_ZOOM)
    max_zoom = NumericProperty(defaultvalue=DEFAULT_MAX_ZOOM)
    bbox = ListProperty(None, allownone=True)

    directory = StringProperty(defaultvalue=DEFAULT_MAPS_DIRECTORY)
    file_basename = StringProperty(defaultvalue=DEFAULT_MAP_BASENAME)
    filepath = StringProperty(None, allownone=True)
    downloading = BooleanProperty(False)
    progress = ListProperty([0,0])
    approximate_size_mb = NumericProperty(0)
    time_to_download = NumericProperty(MAX_DOWNLOAD_TIME)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.progress_bar = None
        self.select_center_button = None
        self.download_button = None
        self.stop_button = None
        self.pause_resume_button = None
        self.downloader = None
        self.info_popup = None
        self.file_exists_popup = None

        self._update_on_provider()
        self._update_filepath()
        self._create_directory_if_not_exists()
        self._init_downloader()
        self._init_popups()

        self.map = self._create_map()
        self._download_panel = self._create_download_panel()
        self.add_widget(self.map)
        self.add_widget(self._download_panel)

        self.bind(
            provider=self._update_on_provider,
            directory=self._update_filepath,
            file_basename=self._update_filepath,
        )

    def _update_on_provider(self, *_):
        if self.provider == CUSTOM_PROVIDER_KEY:
            self.min_zoom = type(self).min_zoom.defaultvalue
            self.max_zoom = type(self).max_zoom.defaultvalue
            self.subdomains = DEFAULT_TILES_SUBDOMAINS
            self.attribution = ''
            self.tile_format = type(self).tile_format.defaultvalue
            self.headers = type(self).headers.defaultvalue
            self.tile_timeout = 0
        else:
            provider_data = PROVIDERS[self.provider]
            self.min_zoom = provider_data.min_zoom
            self.max_zoom = provider_data.max_zoom
            self.subdomains = provider_data.subdomains
            self.provider_url = provider_data.url
            self.attribution = provider_data.attribution
            self.tile_format = provider_data.format
            self.headers = {"User-Agent": provider_data.user_agent}
            self.tile_timeout = provider_data.timeout

    def _update_filepath(self, *_):
        if self.directory and self.file_basename:
            self.filepath = str(Path(self.directory) / f'{self.file_basename}.mbtiles')
        else:
            self.filepath = None

    def _create_directory_if_not_exists(self):
        Path(self.directory).mkdir(parents=True, exist_ok=True)

    def _init_downloader(self):
        self.downloader = downloader = MBTilesDbCache(
            url=self.provider_url,
            zoom_from=self.min_zoom,
            zoom_to=self.zoom_to,
            subdomains=self.subdomains,
            filepath=self.filepath,
            attribution=self.attribution,
            use_attribution=self.use_attribution,
            tile_format=self.tile_format,
            headers=self.headers,
            tile_timeout=self.tile_timeout,
        )
        self.bind(
            provider_url=downloader.setter('url'),
            bbox=downloader.setter('bbox'),
            min_zoom=downloader.setter('zoom_from'),
            zoom_to=downloader.setter('zoom_to'),
            subdomains=downloader.setter('subdomains'),
            filepath=downloader.setter('filepath'),
            attribution=downloader.setter('attribution'),
            tile_format=downloader.setter('tile_format'),
            headers=downloader.setter('headers'),
            tile_timeout=downloader.setter('tile_timeout'),
        )
        downloader.bind(
            downloading=self.setter('downloading'),
            progress=self.setter('progress'),
            approximate_size_mb=self.setter('approximate_size_mb'),
            time_to_download=self.setter('time_to_download'),
            on_success=self.show_success_popup,
            on_error=self.show_exception_popup,
        )

    def show_exception_popup(self, *_):
        self.info_popup.text = f'Map downloading failed.'
        self.info_popup.open()

    def show_success_popup(self, *_):
        self.info_popup.text = f'Map downloading finished successfully.'
        self.info_popup.open()

    def download_with_validation(self, *_):
        if not self.downloader.valid:
            self.info_popup.text = 'Please check the input — some fields are empty or invalid.'
            self.info_popup.open()
            return
        if self.filepath and Path(self.filepath).exists():
            self.file_exists_popup.open()
            return
        self.download()

    def download(self, rewrite=False):
        self.progress = [0,0]
        self.downloader.download(rewrite=rewrite)

    def download_copy(self):
        if self.filepath:
            if not Path(self.filepath).exists():
                self.download()
                return
            match = re.match(r'^(.*?)(\((\d+)\))?$', self.file_basename)
            base_name = match.group(1)
            counter = 1
            new_file_basename = f'{base_name}({counter})'
            while (Path(self.directory) / f'{new_file_basename}.mbtiles').exists():
                counter += 1
                new_file_basename = f'{base_name}({counter})'
            self.file_basename = new_file_basename
            Logger.info(f'Saving copy as "{self.filepath}"')
            self.download()

    def pause(self, *_):
        if self.downloader:
            self.downloader.pause()

    def resume(self, *_):
        if self.downloader:
            self.downloader.resume()

    def stop(self, *_):
        if self.downloader:
            self.downloader.stop()

    def _init_popups(self):
        self.info_popup = InfoPopup(size_hint=(0.5, 0.5))
        self.file_exists_popup = FileExistsPopup(
            size_hint=(0.5, 0.5),
            text='The specified file already exists. Do you want to overwrite it or save copy?',
        )
        self.file_exists_popup.bind(
            on_overwrite=lambda *_: Clock.schedule_once(lambda *_: self.download(True), 0.5),
            on_copy=lambda *_: Clock.schedule_once(lambda *_: self.download_copy(), 0.5),
        )

    def _create_map(self):
        _map = MapPanel(
            url=self.provider_url,
            subdomains=self.subdomains,
            attribution=self.attribution,
            size_hint=(0.75, 1),
            zoom=self.zoom,
            side_in_km=self.side,
        )
        _map.bind(
            zoom=self.setter('zoom'),
            bbox=self.setter('bbox'),
        )
        self.bind(
            side=_map.setter("side_in_km"),
            subdomains=_map.setter("subdomains"),
            provider_url=_map.setter("url"),
            attribution=_map.setter("attribution"),
        )
        return _map

    def _create_download_panel(self):
        download_panel_container = AnchorLayout(
            anchor_x='center',
            anchor_y='center',
            size_hint=(0.25, 1),
            pos_hint={'x': 0.75},
        )
        download_panel = BoxLayoutColored(
            orientation='vertical',
            spacing=5,
            size_hint=(0.92, 0.98),
        )
        download_panel_container.add_widget(download_panel)

        region_section = self.create_region_section()
        download_panel.add_widget(region_section)
        download_panel.add_widget(Widget())

        source_section = self.create_source_section()
        download_panel.add_widget(source_section)
        download_panel.add_widget(Widget())

        zoom_section = self.create_zoom_section()
        download_panel.add_widget(zoom_section)
        download_panel.add_widget(Widget())

        dir_section = self.create_dir_section()
        download_panel.add_widget(dir_section)
        download_panel.add_widget(Widget())

        progress_section = self.create_progress_section()
        download_panel.add_widget(progress_section)
        download_panel.add_widget(Widget())

        return download_panel_container

    def create_region_section(self):
        container_layout = BoxLayoutShort(orientation='vertical')

        header_label_background = BoxLayoutShort(
            padding=(10, 2),
            background=HEADER_BACKGROUND,
        )
        container_layout.add_widget(header_label_background)

        header_label = LabelAutoresized(
            text='REGION (system: WGS84)',
            color=HEADER_TEXT_COLOR,
            font_size=FONT_SIZE_MEDIUM,
        )
        header_label_background.add_widget(header_label)

        choose_on_map_container = AnchorLayout(
            anchor_x='center',
            anchor_y='center',
            size_hint_y=None,
            height=50,
            padding=(0, 6, 0, 4)
        )
        self._init_select_center_button()
        choose_on_map_container.add_widget(self.select_center_button)
        container_layout.add_widget(choose_on_map_container)

        center_label = LabelAutoresized(
            text=f'Center coordinates',
            color=(0.1, 0.1, 0.1, 1),
            font_size=FONT_SIZE_MEDIUM,
        )
        container_layout.add_widget(center_label)

        coords_layout = BoxLayoutShort(
            spacing=5,
            padding=(0,6),
        )

        coords_layout.add_widget(self._create_coord_input(is_lat=True))
        coords_layout.add_widget(self._create_coord_input(is_lat=False))
        container_layout.add_widget(coords_layout)

        container_layout.add_widget(self._create_side_input_layout())

        return container_layout

    def _init_select_center_button(self):
        self.select_center_button = SwitchButtonColored(
            size_hint=(0.8, 1),
            text='Select on map',
            active_text='Cancel selection',
        )
        self.select_center_button.bind(active=self.map.setter('center_selection'))

        def on_downloading(*_):
            if self.downloading:
                self.select_center_button.deactivate()
                self.select_center_button.disabled = True
            else:
                self.select_center_button.disabled = False
        self.bind(downloading=on_downloading)

        def on_center_selected(*_):
            self.select_center_button.deactivate()
        self.map.bind(on_center_selected=on_center_selected)

    def _create_coord_input(self, is_lat=True):
        container = BoxLayoutShort(size_hint_x=0.5, orientation='vertical')
        label = LabelAutoresized(text='Latitude' if is_lat else 'Longitude')
        container.add_widget(label)

        textinput = TextInputCoord(
            is_lat=is_lat,
            size_hint=(None, None),
        )
        textinput.bind(minimum_height=textinput.setter('height'))
        self.bind(downloading=lambda i,v: setattr(textinput, 'readonly', v))

        if is_lat:
            textinput.bind(value=self.map.setter('center_lat'))
            self.map.bind(on_center_selected=lambda *_: textinput.set_text_normalized(self.map.center_lat))
        else:
            textinput.bind(value=self.map.setter('center_lon'))
            self.map.bind(on_center_selected=lambda *_: textinput.set_text_normalized(self.map.center_lon))

        container.bind(width=lambda i, v: setattr(
            textinput, 'width', v - container.padding[0] - container.padding[2]))
        container.add_widget(textinput)

        return container

    def _create_side_input_layout(self):
        layout = TextInputRangedTitledLayout(
            title = f'Side length in km ({self.min_side}-{self.max_side})',
            hint_text = 'Enter side length...',
            text = str(type(self).side.defaultvalue),
            min_value = self.min_side,
            max_value = self.max_side,
            value_setter = self.setter('side'),
        )
        self.bind(downloading=lambda i,v: layout.disable(v))
        return layout

    def create_source_section(self):
        container_layout = BoxLayoutShort(orientation='vertical')

        header_label_background = BoxLayoutShort(
            padding=(10, 2),
            background=HEADER_BACKGROUND,
        )
        container_layout.add_widget(header_label_background)

        header_label = LabelAutoresized(
            text='SOURCE',
            color=HEADER_TEXT_COLOR,
            font_size=FONT_SIZE_MEDIUM,
        )
        header_label_background.add_widget(header_label)

        dropdown = DropDown(auto_width=False,
                            bar_width=6,
                            bar_color=(0.9, 0.1, 0.1, 0.9),
                            bar_inactive_color=(0.9, 0.1, 0.1, 0.3),
                            )
        for provider in (CUSTOM_PROVIDER_KEY, *PROVIDERS.keys()):
            option = Button(text=provider, size_hint_y=None, height=44)
            option.bind(on_release=lambda btn: dropdown.select(btn.text))
            dropdown.add_widget(option)

        container_layout.bind(width=dropdown.setter('width'))

        select_layout = BoxLayoutShort()
        container_layout.add_widget(select_layout)

        provider_label = ProviderLabel(
            text=self.provider,
            valign='middle',
            halign='center',
            size_hint_y=None,
            height=37,
        )
        self.bind(provider=provider_label.setter('text'))

        dropdown_button = ButtonImage(
            size_hint=(None, None),
            size=(33, 33),
            image=DROPDOWN_DOWN_PNG,
        )
        self.bind(downloading=lambda i, v: setattr(dropdown_button, 'disabled', v))
        dropdown.bind(
            on_dismiss=lambda *_: dropdown_button.set_image(DROPDOWN_DOWN_PNG),
            on_select=self.setter('provider'),
        )

        def _on_press(*_):
            if not self.downloading:
                dropdown_button.background_color = (*dropdown_button.background_color[:3], 0.5)

        def _on_release(*_):
            if not self.downloading:
                dropdown_button.background_color = (*dropdown_button.background_color[:3], 1)
                dropdown_button.set_image(DROPDOWN_UP_PNG)
                dropdown.open(provider_label)

        provider_label.bind(
            on_press=_on_press,
            on_release=_on_release,
        )
        dropdown_button.bind(
            on_press=_on_press,
            on_release=_on_release,
        )

        select_layout.add_widget(provider_label)
        select_layout.add_widget(dropdown_button)

        source_input_layout = GridLayout(
            padding = (6,0),
            rows=2,
            cols=1,
            size_hint_y = None,
        )
        source_input_layout.bind(minimum_height=source_input_layout.setter('height'))

        source_label = LabelAutoresized(text='Map Tile Source')
        source_input_layout.add_widget(source_label)

        source_input = TextInputUnderlined(
            text=self.provider_url,
            hint_text="Enter Map Tile Source url...",
            multiline=False,
            size_hint=(None, None),
            padding=(0, 6),
            readonly=True,
        )
        source_input.bind(minimum_height=source_input.setter('height'))
        self.bind(downloading=lambda i, v: setattr(source_input, 'readonly', v))

        source_input_layout.bind(width=lambda i,v: setattr(
            source_input, 'width', v - source_input_layout.padding[0] - source_input_layout.padding[2]))
        source_input_layout.add_widget(source_input)

        def _refresh_cursor(*_):
            source_input.cursor = (0, 0)
            source_input.scroll_x = 0
        trigger_refresh_cursor = Clock.create_trigger(_refresh_cursor)

        def _on_provider(_,v):
            if v == CUSTOM_PROVIDER_KEY:
                source_input.text = ''
                source_input.readonly = False
            else:
                source_input.text = PROVIDERS[v].url
                source_input.readonly = True
            trigger_refresh_cursor()
        self.bind(provider=_on_provider)
        source_input.bind(text=lambda i,v: setattr(self, 'provider_url', v.strip()))
        trigger_refresh_cursor()

        container_layout.add_widget(source_input_layout)
        return container_layout

    def create_zoom_section(self):
        container_layout = BoxLayoutShort(orientation='vertical')
        header_label_background = BoxLayoutShort(
            padding=(10, 2),
            background=HEADER_BACKGROUND,
        )
        container_layout.add_widget(header_label_background)

        header_label = LabelAutoresized(
            text='ZOOM',
            color=HEADER_TEXT_COLOR,
            font_size=FONT_SIZE_MEDIUM,
        )
        header_label_background.add_widget(header_label)

        current_zoom_label = LabelAutoresized(
            text=f'Current: {self.zoom}',
            size_hint_x=1,
            color=(0.1, 0.1, 0.1, 1),
        )
        self.bind(zoom=lambda i,v: setattr(current_zoom_label, 'text', f'Current: {v}'))
        container_layout.add_widget(Widget(size_hint_y=None, height=5))
        container_layout.add_widget(current_zoom_label)

        container_layout.add_widget(self._create_zoom_input_layout())

        return container_layout

    def _create_zoom_input_layout(self):
        layout = TextInputRangedTitledLayout(
            title='Max zoom',
            hint_text='zoom level...',
            text=str(type(self).zoom_to.defaultvalue),
            min_value=self.min_zoom,
            max_value=self.max_zoom,
            value_setter=self.setter('zoom_to'),
        )
        self.bind(
            downloading=lambda i, v: layout.disable(v),
            min_zoom=layout.setter('min_value'),
            max_zoom=layout.setter('max_value'),
        )
        return layout

    def create_dir_section(self):
        root_container = BoxLayoutShort(orientation='vertical')

        header_label_background = BoxLayoutShort(
            padding=(10, 2),
            background=HEADER_BACKGROUND,
        )
        root_container.add_widget(header_label_background)

        header_label = LabelAutoresized(
            text='FILE SAVE OPTIONS',
            color=HEADER_TEXT_COLOR,
            font_size=FONT_SIZE_MEDIUM,
        )
        header_label_background.add_widget(header_label)

        root_container.add_widget(Widget(size_hint_y=None, height=5))

        dirselect_layout = TextInputTitledLayout(
            title='Directory',
            text=str(Path(self.directory).absolute()),
            button_image=FOLDER_PNG,
        )
        dir_textinput = dirselect_layout.textinput
        dir_textinput.readonly = True
        dir_textinput.multiline = False
        dir_textinput.disabled_foreground_color=TextInputUnderlined.foreground_color.defaultvalue
        self.bind(directory=lambda i,v: setattr(dir_textinput, 'text', str(Path(v).absolute())))
        self.bind(downloading=lambda i, v: setattr(dirselect_layout.button, 'disabled', v))

        file_chooser = FileChooserPopup(path=self.directory, size_hint=(.5,.75))
        file_chooser.bind(selected_dir=self.setter('directory'))

        dirselect_layout.button.bind(on_release=lambda *_: file_chooser.open())

        root_container.add_widget(dirselect_layout)

        root_container.add_widget(Widget(size_hint_y=None, height=13))
        filename_label = LabelAutoresized(text='Filename')
        root_container.add_widget(filename_label)

        file_basename_input_layout = RelativeLayout(
            size_hint_y=None,
            height=22,
        )
        root_container.add_widget(file_basename_input_layout)

        filename_textinput = TextInputUnderlined(
            disabled_foreground_color=TextInputUnderlined.foreground_color.defaultvalue,
            text=self.file_basename,
            size_hint=(None, None),
            multiline=False,
            pos_hint={"center_y": 0.5},
        )
        filename_textinput.bind(minimum_height=filename_textinput.setter('height'))
        filename_textinput.bind(text=self.setter('file_basename'))
        self.bind(file_basename=lambda i, v: setattr(filename_textinput, 'text', v))
        self.bind(downloading=lambda i, v: setattr(filename_textinput, 'readonly', v))

        def _fill_input_if_file(*_):
            if file_chooser.selected_file:
                filename_textinput.text = Path(file_chooser.selected_file).stem
        file_chooser.bind(on_submit=_fill_input_if_file)

        extention_label = LabelAutoresized(text='.mbtiles',
                                           pos_hint={"center_y": 0.4})

        filename_textinput.bind(right=lambda i, v: setattr(extention_label, 'x', v))

        file_basename_input_layout.bind(width=lambda i, v: setattr(filename_textinput, 'width', v - extention_label.width))
        extention_label.bind(width=lambda i, v: setattr(filename_textinput, 'width', file_basename_input_layout.width - v))
        file_basename_input_layout.add_widget(filename_textinput)
        file_basename_input_layout.add_widget(extention_label)

        def format_approximate_size(size_mb):
            return f'Approximate size: {size_mb} MB'
        approximate_size_label = LabelAutoresized(
            text=format_approximate_size(self.approximate_size_mb),
            size_hint_x=1,
        )
        self.bind(
            approximate_size_mb=lambda i,v: setattr(approximate_size_label, 'text', format_approximate_size(v))
        )
        root_container.add_widget(Widget(size_hint_y=None, height=12))
        root_container.add_widget(approximate_size_label)

        time_label = LabelAutoresized(size_hint_x=1)
        def update_time_label_text(*_):
            if self.time_to_download == MAX_DOWNLOAD_TIME:
                formated_time = '__m __s'
            else:
                formated_time = format_seconds(self.time_to_download)
            if self.downloading:
                time_label.text = f'Time remaining: {formated_time}'
            else:
                time_label.text = f'Estimated time: {formated_time}'
        self.bind(time_to_download=update_time_label_text)
        update_time_label_text()
        root_container.add_widget(Widget(size_hint_y=None, height=5))
        root_container.add_widget(time_label)

        return root_container

    def create_progress_section(self):
        container = AnchorLayout(anchor_x='center', anchor_y='bottom', height=60, size_hint_y=None)

        self.download_button = download_button = ButtonColored(
            size_hint=(0.8, 1),
            text='DOWNLOAD',
            on_release=self.download_with_validation,
        )
        def set_download_disabled(*_):
            download_button.disabled = not self.downloader.valid or self.downloader.downloading
        self.bind(downloading=set_download_disabled)
        self.downloader.bind(valid=set_download_disabled)
        set_download_disabled()

        self.progress_bar = ProgressBar(value=self.progress[0], max=self.progress[1])
        label = LabelAutoresized(text='0% (0/0)',
                                 size_hint_x=1,
                                 halign='center')
        def _update_progress(*_):
            current = self.progress[0]
            total = self.progress[1]
            self.progress_bar.max = total
            self.progress_bar.value = current
            label.text = f'{round(self.progress_bar.value_normalized * 100, 2) }% ({current}/{total})'
        self.bind(progress=_update_progress)

        progress_container = BoxLayout(orientation='vertical')
        bar_container = BoxLayout(
            size_hint_y=0.5,
            orientation='vertical')

        bar_container.add_widget(self.progress_bar)
        bar_container.add_widget(label)
        bar_container.add_widget(Widget())

        progress_buttons_container = BoxLayout(size_hint_y=0.5)

        progress_container.add_widget(bar_container)
        progress_container.add_widget(progress_buttons_container)

        self.stop_button = ButtonColored(
            size_hint=(0.35, 1),
            text='STOP',
            on_release=self.stop,
        )

        self.pause_resume_button = SwitchButtonColored(
            size_hint=(0.35, 1),
            text='PAUSE',
            active_text='RESUME'
        )
        def pause_resume(*_):
            if self.pause_resume_button.active:
                self.pause()
            else:
                self.resume()
        self.pause_resume_button.bind(active=pause_resume)

        progress_buttons_container.add_widget(Widget(size_hint_x=0.1))
        progress_buttons_container.add_widget(self.stop_button)
        progress_buttons_container.add_widget(Widget(size_hint_x=0.1))
        progress_buttons_container.add_widget(self.pause_resume_button)
        progress_buttons_container.add_widget(Widget(size_hint_x=0.1))

        def show_relevant_buttons(*_):
            container.clear_widgets()
            downloading = self.downloading
            self.stop_button.disabled = not downloading
            self.pause_resume_button.disabled = not downloading
            if downloading:
                container.add_widget(progress_container)
            else:
                container.add_widget(self.download_button)
                self.pause_resume_button.deactivate()

        self.bind(downloading=show_relevant_buttons)
        show_relevant_buttons()

        return container
