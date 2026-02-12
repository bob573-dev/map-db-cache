from setup import setup

setup()

import os

from kivy.core.window import Window
from kivy.properties import ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from wakepy import keep

from localization import LocalizedApp, _
from MBTilesDbCacheLayout import MBTilesDbCacheLayout
from consts import DEFAULT_MAPS_DIRECTORY
from tools.utils import str_to_list


class MBTilesDbCacheApp(LocalizedApp):
    title = 'Map Cache'
    touch_filter = ListProperty([])

    def build_config(self, config):
        config.adddefaultsection('input')
        config.setdefault('input', 'touch_filter', 'mouse')

    def on_stop(self):
        self.main_layout.downloader.clear_cache()

    def build(self):
        Window.bind(on_request_close=self.on_request_close)
        self._update_touch_filter()

        self.main_layout = MBTilesDbCacheLayout(directory=os.getenv('MAP_DIR', DEFAULT_MAPS_DIRECTORY))
        return self.main_layout

    @keep.running
    def run(self):
        super().run()

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
    MBTilesDbCacheApp(lang=os.getenv('ANTIBUG_LANG', default='ua')).run()
