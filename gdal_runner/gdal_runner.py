import os
import platform
import subprocess
import sys
import threading
from pathlib import Path

from kivy.clock import Clock
from kivy.logger import Logger

from utils import SingletonMeta


class GDALRunner(metaclass=SingletonMeta):
    TOOLS = [
        ('gdal_translate', ['gdal_translate', '--version']),
        ('gdalbuildvrt', ['gdalbuildvrt', '--version']),
    ]

    def __init__(self):
        self._is_installed_callbacks = []
        self._is_installed = threading.Event()
        self._setup_finished = threading.Event()

        self._gdal_dir = Path(__file__).parent / ('gdal_win' if self.is_win_platform else 'gdal_linux')
        self._lib_dir = self._gdal_dir / 'lib'
        self._bin_dir = self._gdal_dir / 'bin'
        self._data_dir = self._gdal_dir / 'data'
        self._plugins_dir = self._gdal_dir / "plugins" / "gdal"

        self._env = {}
        self._subprocess_kwargs = {'env': self._env, 'cwd': self._bin_dir}
        if self.is_win_platform:
            self._subprocess_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

        self._run_setup_process()

    @property
    def is_win_platform(self):
        return platform.system() == 'Windows'

    @property
    def is_running_in_bundle(self):
        return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

    def _run_setup_process(self):
        def target():
            self._init_env()
            self._init_is_installed()

        threading.Thread(target=target, name='map-db-cache. GDAL setup process', daemon=True).start()

    def _init_env(self):
        env = os.environ.copy()
        env["PATH"] = str(self._bin_dir) + os.pathsep + str(self._lib_dir) + os.pathsep + env["PATH"]
        if not self.is_win_platform:
            env["LD_LIBRARY_PATH"] = str(self._lib_dir) + os.pathsep + env.get("LD_LIBRARY_PATH", "")
        env["GDAL_DATA"] = str(self._data_dir / "gdal")
        env["PROJ_LIB"] = str(self._data_dir / "proj")
        env["PROJ_DATA"] = str(self._data_dir / "proj")
        if self.is_win_platform:
            env["GDAL_DRIVER_PATH"] = str(self._plugins_dir)
        self._env.update(env)

    def _init_is_installed(self):
        try:
            if self._check_gdal_installed():
                self._is_installed.set()
        except Exception as exc:
            Clock.schedule_once(
                lambda *_, e=exc: Logger.exception(
                    'GDALRunner: _init_is_installed had unexpected exception', exc_info=e
                )
            )
        finally:
            self._setup_finished.set()
            Clock.schedule_once(self._call_is_installed_callbacks)

    def _check_gdal_installed(self) -> bool:
        for tool_name, check_cli in self.TOOLS:
            try:
                cmd = self._generate_command(check_cli)
                subprocess.check_output(cmd, **self._subprocess_kwargs)
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                Clock.schedule_once(
                    lambda *_, e=exc: Logger.exception(
                        f'GDALRunner: Tool "{tool_name}" not found or has problems',
                        exc_info=e,
                    )
                )
                return False
        return True

    def _generate_command(self, cmd) -> list[str]:
        return [str(self._bin_dir / cmd[0])] + cmd[1:]

    def _call_is_installed_callbacks(self, *_):
        for func in self._is_installed_callbacks:
            func(self._is_installed.is_set())
        self._is_installed_callbacks.clear()

    def notify_is_installed_or_not(self, setter_func):
        if self._setup_finished.is_set():
            setter_func(self._is_installed.is_set())
        else:
            self._is_installed_callbacks.append(setter_func)

    def run(self, cmd):
        cmd = self._generate_command(cmd)
        subprocess.run(cmd, **self._subprocess_kwargs)


__all__ = ['GDALRunner']
