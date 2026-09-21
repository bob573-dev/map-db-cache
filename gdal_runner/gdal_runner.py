import importlib
import subprocess
import sys
from pathlib import Path
import threading
import os

from kivy.clock import Clock
from kivy.logger import Logger

from utils import is_win_platform
from utils import SingletonMeta


class GDALRunner(metaclass=SingletonMeta):
    CLI_TOOLS = [
        ('gdal_translate', ['gdal_translate', '--version']),
        ('gdalbuildvrt', ['gdalbuildvrt', '--version']),
        ('gdalwarp', ['gdalwarp', '--version']),
        ('gdaldem', ['gdaldem', '--help']),
        ('gdal_contour', ['gdal_contour', '--help']),
        ('gdal_rasterize', ['gdal_rasterize', '--version']),
        ('ogr2ogr', ['ogr2ogr', '--version']),
    ]
    PY_TOOLS = [
        ('gdal_calc', 'osgeo_utils.gdal_calc'),
        ('gdal2tiles', 'osgeo_utils.gdal2tiles'),
        ('gdal_merge', 'osgeo_utils.gdal_merge'),
    ]

    def __init__(self):
        self._is_installed_callbacks = []
        self._is_installed = threading.Event()
        self._setup_finished = threading.Event()

        self._env = {}
        self._subprocess_kwargs = {'env': self._env}

        self.is_win_platform = is_win_platform()
        self._linux_bundle_dir = Path(__file__).parent / 'gdal_linux'
        self._use_linux_bundle = not self.is_win_platform and (self._linux_bundle_dir / 'bin').is_dir()

        if self.is_win_platform:
            self._gdal_dir = Path(__file__).parent / 'gdal_win'
            self._osgeo4w_dir = self._gdal_dir / 'OSGeo4W'
            self._scripts_dir = self._osgeo4w_dir / 'apps' / 'Python312' / 'Scripts'
            self._bin_dir = self._osgeo4w_dir / 'bin'
            self._gdal_data_dir = self._osgeo4w_dir / 'apps' / 'gdal' / 'share' / 'gdal'
            self._gdal_driver_dir = self._osgeo4w_dir / 'apps' / 'gdal' / 'lib' / 'gdalplugins'
            self._openssl_engines = self._osgeo4w_dir / 'lib' / 'engines-3'
            self._proj_data = self._osgeo4w_dir / 'share' / 'proj'
            self._python_home = self._osgeo4w_dir / 'apps' / 'Python312'
            self._ssl_cert_dir = self._osgeo4w_dir / 'apps' / 'openssl' / 'certs'
            self._ssl_cert_file = self._osgeo4w_dir / 'bin' / 'curl-ca-bundle.crt'

            self._subprocess_kwargs['cwd'] = self._bin_dir
            self._subprocess_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        elif self._use_linux_bundle:
            self._bin_dir = self._linux_bundle_dir / 'bin'
            self._lib_dir = self._linux_bundle_dir / 'lib'
            self._gdal_data_dir = self._linux_bundle_dir / 'data' / 'gdal'
            self._gdal_driver_dir = self._linux_bundle_dir / 'data' / 'gdalplugins'
            self._proj_data = self._linux_bundle_dir / 'data' / 'proj'

            pylib_dir = self._linux_bundle_dir / 'pylib'
            if pylib_dir.is_dir() and str(pylib_dir) not in sys.path:
                sys.path.insert(0, str(pylib_dir))

        self._run_setup_process()

    def _run_setup_process(self):
        def target():
            self._init_env()
            self._init_is_installed()

        threading.Thread(target=target, name='map-db-cache. GDAL setup process', daemon=True).start()

    def _init_env(self):
        if self.is_win_platform:
            os.environ["PATH"] = (
                str(self._scripts_dir) + os.pathsep + str(self._bin_dir) + os.pathsep + os.environ["PATH"]
            )
            os.environ["GDAL_DATA"] = str(self._gdal_data_dir)
            os.environ["GDAL_DRIVER_PATH"] = str(self._gdal_driver_dir)
            os.environ["OPENSSL_ENGINES"] = str(self._openssl_engines)
            os.environ["OSGEO4W_ROOT"] = str(self._osgeo4w_dir)
            os.environ["PROJ_DATA"] = str(self._proj_data)
            os.environ["PYTHONHOME"] = str(self._python_home)
            os.environ["SSL_CERT_DIR"] = str(self._ssl_cert_dir)
            os.environ["SSL_CERT_FILE"] = str(self._ssl_cert_file)
        elif self._use_linux_bundle:
            # No LD_LIBRARY_PATH here: the collected CLI binaries/libraries resolve each other
            # via the RPATH patched in by collect_gdal_linux.sh, and so does gdal_linux/pylib's
            # osgeo (same RPATH treatment) — so nothing needs a library-search env var.
            os.environ["PATH"] = str(self._bin_dir) + os.pathsep + os.environ["PATH"]
            os.environ["GDAL_DATA"] = str(self._gdal_data_dir)
            os.environ["GDAL_DRIVER_PATH"] = str(self._gdal_driver_dir)
            os.environ["PROJ_DATA"] = str(self._proj_data)
        self._env.update(os.environ)

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

    @staticmethod
    def _import_osgeo_tool(module_name: str):
        try:
            return importlib.import_module(module_name)
        except ImportError:
            return None

    def _get_tools(self) -> list:
        tools = list(self.CLI_TOOLS)
        tools += [(name, ('module', module)) for name, module in self.PY_TOOLS]
        return tools

    def _check_gdal_installed(self) -> bool:
        for tool_name, cmd in self._get_tools():
            try:
                if isinstance(cmd, tuple) and cmd[:1] == ('module',):
                    _, module = cmd
                    if not self._import_osgeo_tool(module):
                        raise Exception(f'{tool_name} is missing')
                elif isinstance(cmd, list):
                    self.run(cmd)
            except Exception as exc:
                Clock.schedule_once(
                    lambda *_, e=exc: Logger.exception(
                        f'GDALRunner: Tool "{tool_name}" not found or has problems',
                        exc_info=e,
                    )
                )
                return False
        return True

    def _generate_command(self, cmd) -> list[str]:
        if self.is_win_platform or self._use_linux_bundle:
            return [str(self._bin_dir / cmd[0])] + cmd[1:]
        return cmd

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
        self._exec(self._generate_command(cmd))

    def _exec(self, cmd):
        with subprocess.Popen(cmd, **self._subprocess_kwargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1) as proc:
            for line in proc.stdout:
                Logger.info(f'{line.rstrip()}')
            for line in proc.stderr:
                Logger.error(f'{line.rstrip()}')
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd)

    def gdal_calc(self, gdal_args: list[str]):
        module = self._import_osgeo_tool('osgeo_utils.gdal_calc')
        if not module:
            raise Exception('gdal_calc implementation is missing')
        module.main(gdal_args)

    def gdal2tiles(self, gdal_args: list[str]):
        module = self._import_osgeo_tool('osgeo_utils.gdal2tiles')
        if not module:
            raise Exception('gdal2tiles implementation is missing')
        module.main(gdal_args, called_from_main=True)

    def gdal_merge(self, gdal_args: list[str]):
        module = self._import_osgeo_tool('osgeo_utils.gdal_merge')
        if not module:
            raise Exception('gdal_merge implementation is missing')
        module.main(gdal_args)


__all__ = ['GDALRunner']
