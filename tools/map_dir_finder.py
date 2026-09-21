import os
import re
from pathlib import Path
from typing import Optional

from consts import MAP_DIRECTORY_NAMES

_MAX_SEARCH_DEPTH = 3

_SEPARATOR_RE = re.compile(r'[\s_\-.]+')


def _normalize(name: str) -> str:
    return _SEPARATOR_RE.sub('', name.strip().lower())


_SYNONYM_RANK = {_normalize(name): rank for rank, name in enumerate(MAP_DIRECTORY_NAMES)}


def find_home_map_directory() -> Optional[str]:
    home = Path.home()
    candidates = []
    try:
        for root, dirs, _files in os.walk(home, topdown=True, onerror=lambda _e: None):
            root_path = Path(root)
            depth = len(root_path.relative_to(home).parts)

            dirs[:] = [d for d in dirs if not d.startswith('.')]
            child_depth = depth + 1

            for d in dirs:
                rank = _SYNONYM_RANK.get(_normalize(d))
                if rank is not None:
                    candidates.append((child_depth, rank, root_path / d))

            if child_depth >= _MAX_SEARCH_DEPTH:
                dirs[:] = []
    except OSError:
        return None

    if not candidates:
        return None
    candidates.sort(key=lambda c: (c[0], c[1], str(c[2]).lower()))
    return str(candidates[0][2])
