import logging
import os, sys
from pathlib import Path

import appdirs

DEFAULT_LOG_LEVEL = logging.DEBUG
DEFAULT_LOG_DIR = appdirs.user_log_dir('map-db-cache', 'bob')
DEFAULT_MAXIMIZE = True


def setup():  # should be executed before any kivy import
    log_level = DEFAULT_LOG_LEVEL
    maximize = DEFAULT_MAXIMIZE
    tablet = False

    if '--silent' in sys.argv:
        sys.argv.remove('--silent')
        log_level = logging.WARNING
    if '--verbose' in sys.argv:
        sys.argv.remove('--verbose')
        log_level = logging.INFO
    if '--minimize' in sys.argv:
        sys.argv.remove('--minimize')
        maximize = False
    if '--tablet' in sys.argv:
        sys.argv.remove('--tablet')
        tablet = True

    _setup_keyboard(tablet)
    _setup_logging(log_level)
    _setup_mouse()
    _setup_touch_input(tablet)
    _setup_window(maximize)
    _setup_cursor(tablet)
    _setup_vkeyboard_class(tablet)
    _setup_gdal()

    return tablet


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

    fmt = "%(asctime)s.%(msecs)03d - %(message)s"
    datefmt = "%H:%M:%S"
    for handler in root_logger.handlers:
        handler.setFormatter(logging.Formatter(fmt, datefmt))


def _setup_mouse():
    from kivy.config import Config
    Config.set('input', 'mouse', 'mouse,disable_multitouch')


def _setup_touch_input(tablet):
    if not tablet:
        return

    from utils import is_win_platform
    if is_win_platform():
        return

    from kivy.config import Config
    Config.remove_option('input', '%(name)s')
    Config.set('input', 'touch', 'probesysfs,provider=mtdev,param=rotation=90,param=invert_y=1')


def _setup_cursor(tablet):
    from kivy.core.window import Window
    Window.show_cursor = not tablet


def _setup_window(maximize):
    from kivy.config import Config
    Config.set('graphics', 'minimum_width', '1020')
    Config.set('graphics', 'minimum_height', '820')

    if maximize:
        from kivy.core.window import Window
        Window.maximize()
    else:
        Config.set('graphics', 'width', '1024')
        Config.set('graphics', 'height', '820')


def _setup_gdal():
    from gdal_runner import GDALRunner
    GDALRunner()


def _setup_keyboard(tablet):
    if not tablet:
        return

    from kivy.config import Config
    from kivy.resources import resource_add_path
    from consts import KEYBOARDS_PATH

    Config.set('kivy', 'keyboard_mode', 'systemanddock')
    resource_add_path(str(KEYBOARDS_PATH))


def _setup_vkeyboard_class(tablet):
    if not tablet:
        return

    # deferred until after _setup_mouse()/_setup_window() since importing
    # kivy.core.window.Window instantiates the real window immediately,
    # and doing that any earlier would apply with the wrong mouse/size config
    from kivy.core.window import Window
    from uix.vkeyboard import TabletVKeyboard

    Window.set_vkeyboard_class(TabletVKeyboard)
