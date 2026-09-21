import logging
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import appdirs

from consts import ICON_PNG

logger = logging.getLogger(__name__)


def _desktop_dir() -> Path:
    try:
        result = subprocess.run(['xdg-user-dir', 'DESKTOP'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return Path.home() / 'Desktop'


def _applications_dir() -> Path:
    return Path.home() / '.local' / 'share' / 'applications'


def _stable_launcher_path() -> Path:
    return Path(appdirs.user_data_dir('map-db-cache', 'bob')) / 'MapDbCache'


def _resync_launcher_symlink(launcher_path: Path):
    """
        `Exec=` in the .desktop entry always points at this fixed path, never at `sys.executable`
        directly -- the packaged single-file executable can be anywhere the user put it, and can
        move between runs (rebuilt, relocated, etc). Keeping `Exec=` fixed means the .desktop
        file (and its Nautilus trust flag, see _mark_trusted) never has to be rewritten.

        Instead, this symlink is what tracks the real, possibly-moved executable. Called on every
        startup (not just first-run): repointing a symlink is a handful of bytes, so redoing it
        unconditionally is far cheaper than copying the ~200M executable would be, and it means a
        moved/rebuilt executable self-heals the next time the app happens to be launched directly
        from its new location (a shortcut launched from a stale symlink can't self-heal on its
        own, same limitation any such scheme has).
    """
    current_target = Path(sys.executable).resolve()
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if launcher_path.is_symlink() and launcher_path.readlink() == current_target:
            return
    except OSError:
        pass
    tmp_path = launcher_path.with_name(f'{launcher_path.name}.tmp-{os.getpid()}')
    tmp_path.symlink_to(current_target)
    tmp_path.replace(launcher_path)


def _mark_trusted(desktop_file: Path):
    """
        Nautilus (GNOME Files) treats a Desktop launcher as untrusted -- shows a shield icon and
        refuses to run it on click -- unless it also carries the `metadata::trusted` GIO
        attribute (normally set by the user via right-click -> "Allow Launching"); the
        executable bit alone isn't enough. `gio` may be absent (non-GNOME desktop, minimal
        install) -- best-effort, silently skipped if so.
    """
    try:
        subprocess.run(
            ['gio', 'set', '-t', 'string', str(desktop_file), 'metadata::trusted', 'true'],
            capture_output=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def ensure_desktop_shortcut():
    threading.Thread(target=_ensure_desktop_shortcut, daemon=True).start()


def _ensure_desktop_shortcut():
    """
        Best-effort: registers a .desktop launcher (Desktop icon + application menu entry) for
        the packaged single-file executable, since PyInstaller cannot embed an icon into an ELF
        binary on Linux. The .desktop registration itself is first-run-only; the stable launcher
        symlink it points at (see _resync_launcher_symlink) is refreshed on every call. Never
        raises -- this is a convenience, not something app startup should depend on.
    """
    try:
        launcher_path = _stable_launcher_path()
        _resync_launcher_symlink(launcher_path)

        applications_file = _applications_dir() / 'MapDbCache.desktop'
        if applications_file.exists():
            return

        persistent_icon = Path(appdirs.user_data_dir('map-db-cache', 'bob')) / 'icon.png'
        persistent_icon.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ICON_PNG, persistent_icon)

        entry_contents = (
            "[Desktop Entry]\n"
            "Version=1.0\n"
            "Type=Application\n"
            "Name=MapDbCache\n"
            f'Exec="{launcher_path}"\n'
            f"Icon={persistent_icon}\n"
            "Terminal=false\n"
            "Categories=Utility;\n"
            "StartupWMClass=MapDbCache\n"
        )

        applications_file.parent.mkdir(parents=True, exist_ok=True)
        applications_file.write_text(entry_contents)
        applications_file.chmod(0o755)

        desktop_dir = _desktop_dir()
        if desktop_dir.is_dir():
            desktop_file = desktop_dir / 'MapDbCache.desktop'
            if not desktop_file.exists():
                desktop_file.write_text(entry_contents)
                desktop_file.chmod(0o755)
                _mark_trusted(desktop_file)
    except Exception:
        logger.exception('Failed to create Desktop/application menu shortcut')
