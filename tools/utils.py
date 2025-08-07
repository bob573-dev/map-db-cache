import csv
from datetime import datetime, timezone

def current_year() -> int:
    return datetime.now(timezone.utc).year

def format_seconds(seconds: int) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes:
        return f"{minutes}m {secs}s"
    return f'{secs}s'

def minmax(x, minimum, maximum):
    return max(minimum, min(x, maximum))

def str_to_list(v, default=None):
    if default is None: default = []
    if not v: return default
    if v[0] == '[' and v[-1] == ']': v = v[1:-1].strip()
    return [s.strip() for l in csv.reader([v], skipinitialspace=True) for s in l if s.strip()]

def str_to_bool(s):
    return not s.lower() in ('', '0', 'false', 'no', 'off', '-')
