from setup import setup

TABLET_MODE = setup()

import os
from pathlib import Path

from kivy.base import EventLoop
from kivy.core.window import Window
from kivy.properties import ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.behaviors.focus import FocusBehavior
from wakepy import keep

from localization import LocalizedApp, _
from MBTilesDbCacheLayout import MBTilesDbCacheLayout
from consts import DEFAULT_MAPS_DIRECTORY, ICON_PNG
from tools.map_dir_finder import find_home_map_directory
from tools.touch_calibration_postproc import TouchCalibrationPostproc
from tools.touch_dedup_filter import TouchDedupFilter
from tools.utils import str_to_list
from utils import get_screen_size


class MBTilesDbCacheApp(LocalizedApp):
    title = 'Map Cache'
    touch_filter = ListProperty([])

    def build_config(self, config):
        config.adddefaultsection('input')
        config.set('input', 'touch_filter', 'mouse,touch')
        config.adddefaultsection('storage')
        config.setdefault('storage', 'last_map_directory', '')

    def on_stop(self):
        self.main_layout.downloader.clear_cache()

    def _resolve_map_directory(self) -> str:
        map_dir_env = os.getenv('MAP_DIR')
        if map_dir_env:
            return map_dir_env
        last_map_directory = self.config.get('storage', 'last_map_directory')
        return last_map_directory or find_home_map_directory() or DEFAULT_MAPS_DIRECTORY

    def build(self):
        self.icon = ICON_PNG
        Window.bind(on_request_close=self.on_request_close)
        from kivy.config import Config
        self._docked_keyboard_active = Config.get('kivy', 'keyboard_mode') == 'systemanddock'
        self._setup_touch_calibration()
        self._touch_dedup_filter = None
        self._update_touch_filter()

        self.main_layout = MBTilesDbCacheLayout(directory=self._resolve_map_directory())
        self.main_layout.downloader.bind(on_success=self._remember_last_directory)
        return self.main_layout

    @keep.running
    def run(self):
        super().run()

    def _setup_touch_calibration(self):
        """
            Corrects clicks landing offset from the actual touch point in
            windowed Desktop Mode with decorations: Kivy scales a touch's
            normalized (0-1) position by Window.width/height, implicitly
            assuming the window covers the whole physical screen at (0, 0) --
            with a border/title bar it doesn't, so touches drift further off
            the further they are from the window's own origin.
        """
        if not TABLET_MODE:
            return
        screen_size = get_screen_size()
        if screen_size is None:
            from kivy.logger import Logger
            Logger.warning(
                'MBTilesDbCacheApp: could not determine the physical screen size -- '
                'making the window borderless instead of calibrating touch coordinates'
            )
            Window.borderless = True
            return
        EventLoop.add_postproc_module(TouchCalibrationPostproc(screen_size, Window))

    def _update_touch_filter(self):
        self.touch_filter = str_to_list(self.config.get('input', 'touch_filter'))

        if TABLET_MODE:
            if self._touch_dedup_filter is None:
                self._touch_dedup_filter = TouchDedupFilter(
                    Window, self.touch_filter, on_drop=self._on_touch_dropped,
                )
            else:
                self._touch_dedup_filter.set_devices(self.touch_filter)
            return

        Window.unbind(
            on_touch_down=self._filter_touch_down,
            on_touch_move=self._filter_touch_events,
            on_touch_up=self._filter_touch_events,
        )
        if self.touch_filter:
            Window.bind(
                on_touch_down=self._filter_touch_down,
                on_touch_move=self._filter_touch_events,
                on_touch_up=self._filter_touch_events,
            )

    def _filter_touch_events(self, _, event):
        if event.device not in self.touch_filter:
            return True  # stop further event processing

    def _filter_touch_down(self, _, event):
        if event.device not in self.touch_filter:
            self._ignore_touch_for_docked_keyboard(event)
            return True  # stop further event processing

    def _on_touch_dropped(self, event, phase):
        if phase == 'down':
            self._ignore_touch_for_docked_keyboard(event)

    def _ignore_touch_for_docked_keyboard(self, event):
        if self._docked_keyboard_active:
            if event not in FocusBehavior.ignored_touch:
                FocusBehavior.ignored_touch.append(event)

    def _remember_last_directory(self, *_):
        directory = str(Path(self.main_layout.directory).absolute())
        self.config.set('storage', 'last_map_directory', directory)
        self.config.write()

    def on_request_close(self, *args):
        if self.main_layout.downloading:
            self.show_exit_popup()
            return True
        return False

    def show_exit_popup(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(
            Label(
                text=_("The map is still downloading. \nExiting now will cancel the operation. Continue?"),
                halign='center',
                valign='middle',
                text_size=(600, None),
            )
        )

        buttons = BoxLayout(size_hint_y=None, height=40, spacing=10)
        btn_ok = Button(text=_("Exit"))
        btn_cancel = Button(text=_("Cancel"))

        buttons.add_widget(btn_ok)
        buttons.add_widget(btn_cancel)
        content.add_widget(buttons)

        popup = Popup(
            title=_("Exit confirmation"),
            content=content,
            size_hint=(None, None),
            size=(680, 320),
            auto_dismiss=False,
        )

        btn_cancel.bind(on_release=popup.dismiss)
        btn_ok.bind(on_release=lambda *_: self.force_exit(popup))

        popup.open()

    def force_exit(self, popup):
        popup.dismiss()
        self.stop()
        Window.close()


if __name__ == '__main__':
    import sys
    from kivy.resources import resource_add_path

    if hasattr(sys, '_MEIPASS'):
        resource_add_path(os.path.join(sys._MEIPASS))
    MBTilesDbCacheApp(lang=os.getenv('MAP_DB_CACHE_LANG', default='ua')).run()
