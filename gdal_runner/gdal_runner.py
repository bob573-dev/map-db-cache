import os
import platform
import subprocess
import sys
from pathlib import Path

from kivy.logger import Logger


TOOLS = [
    ('gdal_translate', ['gdal_translate', '--version']),
    ('gdalbuildvrt', ['gdalbuildvrt', '--version']),
]


def _is_running_in_bundle():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def check_gdal_installed() -> bool:
    check_command = _check_gdal_command_win if platform.system() == 'Windows' else _check_gdal_command_linux
    for tool_name, check_cli in TOOLS:
        try:
            check_command(check_cli)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            Logger.exception(f'GDAL runner: Tool "{tool_name}" not found or not usable.', exc_info=exc)
            return False
    return True


def _check_gdal_command_win(cmd):
    if _is_running_in_bundle():
        exe_path = Path(__file__).parent.parent / 'gdal_win_runner.exe'
        subprocess.check_output([exe_path] + cmd)
    else:
        env, bin_dir = prepare_gdal_env(win=True)
        subprocess.check_output([str(bin_dir / cmd[0])] + cmd[1:], env=env, creationflags=subprocess.CREATE_NO_WINDOW)


def _check_gdal_command_linux(cmd):
    env, bin_dir = prepare_gdal_env()
    subprocess.check_output([str(bin_dir / cmd[0])] + cmd[1:], env=env, creationflags=subprocess.CREATE_NO_WINDOW)


def prepare_gdal_env(win=False) -> tuple[dict, Path]:
    base = (Path(__file__).parent / ('gdal_win' if win else 'gdal_linux')).absolute()
    bin_dir = base / "bin"
    lib_dir = base / "lib"
    data_dir = base / "data"
    plugins_dir = base / "plugins" / "gdal"

    env = os.environ.copy()
    env["PATH"] = str(bin_dir) + os.pathsep + str(lib_dir) + os.pathsep + env["PATH"]
    # Linux-specific
    env["LD_LIBRARY_PATH"] = str(lib_dir) + os.pathsep + env.get("LD_LIBRARY_PATH", "")
    # GDAL data
    env["GDAL_DATA"] = str(data_dir / "gdal")
    env["PROJ_LIB"] = str(data_dir / "proj")
    env["PROJ_DATA"] = str(data_dir / "proj")

    if plugins_dir.exists():
        env["GDAL_DRIVER_PATH"] = str(plugins_dir)

    return env, bin_dir


def run_gdal(cmd):
    if platform.system() == 'Windows':
        _run_gdal_win(cmd)
    else:
        _run_gdal_linux(cmd)


def _run_gdal_linux(cmd):
    env, bin_dir = prepare_gdal_env()
    subprocess.run([str(bin_dir / cmd[0])] + cmd[1:], env=env, creationflags=subprocess.CREATE_NO_WINDOW)


def _run_gdal_win(cmd):
    if _is_running_in_bundle():
        exe_path = Path(__file__).parent.parent / 'gdal_win_runner.exe'
        subprocess.run([exe_path] + cmd)
    else:
        env, bin_dir = prepare_gdal_env(win=True)
        subprocess.run([str(bin_dir / cmd[0])] + cmd[1:], env=env, creationflags=subprocess.CREATE_NO_WINDOW)


__all__ = [
    'check_gdal_installed',
    'prepare_gdal_env',
    'run_gdal',
]
