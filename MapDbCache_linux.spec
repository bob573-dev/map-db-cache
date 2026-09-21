# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

python_site_packages = Path(sys.executable).parent.parent / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"

datas = [
    ('png', 'png'),
    ('keyboards', 'keyboards'),
    ('locales', 'locales'),
    (str(python_site_packages / 'kivy_garden' / 'mapview' / 'icons'), 'kivy_garden/mapview/icons'),
    # Kivy fonts
    *[(str(f), "data/fonts") for f in (python_site_packages / "kivy" / "data" / "fonts").glob("*.ttf")],
    # GDAL
    ('./gdal_runner/gdal_linux', './gdal_runner/gdal_linux'),
]

hiddenimports = [
    'kivy_garden.mapview.mapview',
    'kivy_garden.mapview.tilesource',
    'kivy_garden.mapview.providers',
]

args_hook_path = Path('linux_runtime_args_hook.py')
runtime_hooks = [str(args_hook_path)] if args_hook_path.exists() else []

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MapDbCache',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None, # See tools/desktop_shortcut.py for how the app gets a real icon.
)
