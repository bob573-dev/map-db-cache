from setup import setup
from tools.utils import str_to_list

setup()

import os

from kivy.app import App
from kivy.core.window import Window
from kivy.properties import ListProperty


from MBTilesDbCacheLayout import MBTilesDbCacheLayout
from consts import DEFAULT_MAPS_DIRECTORY


class MBTilesDbCacheApp(App):
    title = 'Map Cache'
    touch_filter = ListProperty([])

    def build_config(self, config):
        config.adddefaultsection('input')
        config.setdefault('input', 'touch_filter', 'mouse')

    def on_stop(self):
        self.main_layout.downloader.clear_cache()

    def build(self):
        self._update_touch_filter()
        self.main_layout = MBTilesDbCacheLayout(
            directory=os.getenv('MAP_DIR', DEFAULT_MAPS_DIRECTORY)
        )
        return self.main_layout

    def _update_touch_filter(self):
        Window.unbind(
            on_touch_down=self._filter_touch_events,
            on_touch_move=self._filter_touch_events,
            on_touch_up=self._filter_touch_events,
            )
        self.touch_filter = str_to_list(self.config.get('input', 'touch_filter'))
        if self.touch_filter:
            Window.bind(
                on_touch_down=self._filter_touch_events,
                on_touch_move=self._filter_touch_events,
                on_touch_up=self._filter_touch_events,
                )

    def _filter_touch_events(self, _, event):
        if event.device not in self.touch_filter:
            return True  # stop further event processing


if __name__ == '__main__':
    import sys
    from kivy.resources import resource_add_path

    if hasattr(sys, '_MEIPASS'):
        resource_add_path(os.path.join(sys._MEIPASS))
    MBTilesDbCacheApp().run()
