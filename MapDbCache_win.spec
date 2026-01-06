# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path
from kivy_deps import sdl2, glew

from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_dynamic_libs

block_cipher = None

python_site_packages = Path(sys.executable).parent.parent.parent / "Python312" / "Lib" / "site-packages"

binaries = []
binaries += [(str(f), '.') for f in sdl2.dep_bins]
binaries += [(str(f), '.') for f in glew.dep_bins]

datas = [
    ('png', 'png'),
    ('locales', 'locales'),
    (str(python_site_packages / 'kivy_garden' / 'mapview' / 'icons'), 'kivy_garden/mapview/icons'),
    # Kivy fonts
    *[(str(f), "data/fonts") for f in (python_site_packages / "kivy" / "data" / "fonts").glob("*.ttf")],
    # GDAL
    ('./gdal_runner/gdal_win/OSGeo4W', './gdal_runner/gdal_win/OSGeo4W'),
]

hiddenimports = [
    'kivy_garden.mapview.mapview',
    'kivy_garden.mapview.tilesource',
    'kivy_garden.mapview.providers',
    'win32timezone',
    'osgeo',
    'osgeo.gdal',
    'osgeo.ogr',
    'osgeo.osr',
    *collect_submodules("osgeo"),
    'osgeo_utils',
    'osgeo_utils.gdal2tiles',
    'osgeo_utils.gdal_calc',
    'osgeo_utils.auxiliary',
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
