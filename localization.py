import gettext
import os
from pathlib import Path

from kivy.app import App
from kivy.logger import Logger
from kivy.properties import StringProperty

from consts import LOCALES_DOMAIN


def _(message):
    app = App.get_running_app()
    if isinstance(app, LocalizedApp):
        return app.gettext(message)
    return message


class LocalizedApp(App):
    LOCALES_DIR = Path(os.path.dirname(__file__)) / 'locales'
    lang = StringProperty('en', allownone=True)

    def __init__(self, **kwargs):
        gettext.bindtextdomain(LOCALES_DOMAIN, self.LOCALES_DIR)
        super().__init__(**kwargs)
        self.translation = None
        self._locales = []
        self._init_locales()
        self.on_lang()

    def _init_locales(self):
        self._locales = [f.name for f in self.LOCALES_DIR.iterdir() if f.is_dir()]
        Logger.info(f'Localization: Available languages: {self._locales}')
        if self.lang not in self._locales:
            if self._locales:
                self.lang = self._locales[0]
            else:
                self.lang = None

    def _init_translation(self):
        if self.lang is None:
            self.translation = None
        else:
            self.translation = gettext.translation(
                LOCALES_DOMAIN, self.LOCALES_DIR, languages=[self.lang], fallback=True
            )

    def on_lang(self, *args):
        self._init_translation()
        Logger.info(f'Localization: Active language: {self.lang}')

    def gettext(self, message):
        return self.translation.gettext(message) if self.translation else message
