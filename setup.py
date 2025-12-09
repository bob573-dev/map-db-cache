import logging
import os, sys
from pathlib import Path

DEFAULT_LOG_LEVEL = logging.DEBUG
DEFAULT_LOG_DIR = 'logs'
DEFAULT_MAXIMIZE = False


def setup():  # should be executed before any kivy import
    log_level = DEFAULT_LOG_LEVEL
    maximize = DEFAULT_MAXIMIZE

    if '--silent' in sys.argv:
        sys.argv.remove('--silent')
        log_level = logging.WARNING
    if '--verbose' in sys.argv:
        sys.argv.remove('--verbose')
        log_level = logging.INFO
    if '--maximize' in sys.argv:
        sys.argv.remove('--maximize')
        maximize = True

    _setup_logging(log_level)
    _setup_mouse()
    _setup_window(maximize)
    _setup_cursor()


def _setup_logging(level):
    if sys.__stdout__ is None or sys.__stderr__ is None:
        os.environ['KIVY_NO_CONSOLELOG'] = '1'

    from kivy.config import Config
    Config.set('kivy', 'log_dir', Path(DEFAULT_LOG_DIR).absolute())

    from kivy.logger import Logger
    level_name = logging._levelToName[level].lower()
    Logger.info(f'Setting log level to "{level_name}"')
    Config.set('kivy', 'log_level', level_name)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        handler.setLevel(level)


def _setup_mouse():
    from kivy.config import Config
    Config.set('input', 'mouse', 'mouse,disable_multitouch')


def _setup_cursor():
    from kivy.core.window import Window
    Window.show_cursor = True


def _setup_window(maximize):
    from kivy.config import Config
    Config.set('graphics', 'minimum_width', '860')
    Config.set('graphics', 'minimum_height', '794')

    if maximize:
        from kivy.core.window import Window
        Window.maximize()
    else:
        Config.set('graphics', 'width', '1024')
        Config.set('graphics', 'height', '800')
