# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path
from kivy_deps import sdl2, glew

block_cipher = None

python_site_packages = Path(sys.executable).parent.parent / "Lib" / "site-packages"

binaries = []
binaries += [(str(f), '.') for f in sdl2.dep_bins]
binaries += [(str(f), '.') for f in glew.dep_bins]

datas = [
    ('png', 'png'),
    ('locales', 'locales'),
    (str(python_site_packages / 'kivy_garden' / 'mapview' / 'icons'), 'kivy_garden/mapview/icons'),
    # Kivy fonts
    *[(str(f), "data/fonts") for f in (python_site_packages / "kivy" / "data" / "fonts").glob("*.ttf")],
]

hiddenimports = [
    'kivy_garden.mapview.mapview',
    'kivy_garden.mapview.tilesource',
    'kivy_garden.mapview.providers',
    'win32timezone',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
    icon=['icon.ico'],
)
