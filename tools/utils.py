import os, sys
import csv
import shutil
from datetime import datetime, timezone
from pathlib import Path

from pathvalidate import is_valid_filepath

from localization import _


def current_year() -> int:
    return datetime.now(timezone.utc).year

def format_seconds(seconds: int) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes:
        return f'{minutes}' + _('m') + f' {secs}' + _('s')
    return f'{secs}' + _('s')

def minmax(x, minimum, maximum):
    return max(minimum, min(x, maximum))

def str_to_list(v, default=None):
    if default is None: default = []
    if not v: return default
    if v[0] == '[' and v[-1] == ']': v = v[1:-1].strip()
    return [s.strip() for l in csv.reader([v], skipinitialspace=True) for s in l if s.strip()]

def str_to_bool(s):
    return not s.lower() in ('', '0', 'false', 'no', 'off', '-')

def check_filepath_valid(filepath):
    platform = None
    if sys.platform.startswith("win"):
        platform = 'Windows'
    elif sys.platform.startswith("darwin"):
        platform = 'macOS'
    elif sys.platform.startswith("linux"):
        platform = 'Linux'
    elif os.name == "posix":
        platform = 'POSIX'
    return is_valid_filepath(filepath, platform=platform)

def try_delete_directory(path: str):
    if Path(path).is_dir():
        try:
            shutil.rmtree(path)
        except:
            shutil.rmtree(path, ignore_errors=True)
