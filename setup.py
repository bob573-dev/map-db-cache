import logging
import sys
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
    _setup_window(maximize)
    _setup_cursor()


def _setup_logging(level):
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


def _setup_cursor():
    from kivy.core.window import Window
    Window.show_cursor = True


def _setup_window(maximize):
    from kivy.config import Config
    Config.set('graphics', 'minimum_width', '860')
    Config.set('graphics', 'minimum_height', '730')

    if maximize:
        from kivy.core.window import Window
        Window.maximize()
    else:
        Config.set('graphics', 'width', '1024')
        Config.set('graphics', 'height', '768')
