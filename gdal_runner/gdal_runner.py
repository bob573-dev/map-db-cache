import subprocess
from pathlib import Path
import threading

from kivy.clock import Clock
from kivy.logger import Logger

from utils import is_win_platform

try:
    from osgeo_utils.gdal_calc import *  # noqa
    from osgeo_utils.gdal_calc import main as gdal_calc_main

    from osgeo_utils.gdal2tiles import *  # noqa
    from osgeo_utils.gdal2tiles import main as gdal2tiles_main
except ImportError:
    gdal_calc_main = None
    gdal2tiles_main = None

from utils import SingletonMeta


class GDALRunner(metaclass=SingletonMeta):
    TOOLS = [
        ('gdal_translate', ['gdal_translate', '--version']),
        ('gdalbuildvrt', ['gdalbuildvrt', '--version']),
        ('gdalwarp', ['gdalwarp', '--version']),
        ('gdaldem', ['gdaldem', '--help']),
        ('gdal_contour', ['gdal_contour', '--help']),
        ('gdal_rasterize', ['gdal_rasterize', '--version']),
        ('ogr2ogr', ['ogr2ogr', '--version']),
        ('gdal_calc', []),
        ('gdal2tiles', []),
    ]

    def __init__(self):
        self._is_installed_callbacks = []
        self._is_installed = threading.Event()
        self._setup_finished = threading.Event()

        self._env = {}
        self._subprocess_kwargs = {'env': self._env}

        self.is_win_platform = is_win_platform()
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

        self._run_setup_process()

    @property
    def is_running_in_bundle(self):
        return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

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

    def _check_gdal_installed(self) -> bool:
        for tool_name, check_cli in self.TOOLS:
            try:
                if tool_name == 'gdal_calc':
                    if not gdal_calc_main:
                        raise ImportError
                elif tool_name == 'gdal2tiles':
                    if not gdal2tiles_main:
                        raise ImportError
                else:
                    cmd = self._generate_command(check_cli)
                    subprocess.check_output(cmd, **self._subprocess_kwargs)
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
        if self.is_win_platform:
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
        cmd = self._generate_command(cmd)
        subprocess.run(cmd, **self._subprocess_kwargs, check=True)

    def gdal_calc(self, gdal_args: list[str]):
        gdal_calc_main(gdal_args)

    def gdal2tiles(self, gdal_args: list[str]):
        gdal2tiles_main(gdal_args, called_from_main=True)


__all__ = ['GDALRunner']
