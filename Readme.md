# MapDbCache

## Linux
### Requirements
python >= 3.11.11 \
libgdal (3.12.1 or greater) \
numpy (1.0.0 or greater) \
setuptools (python) \
wheel (python)

### Setup
```
./install_with_sourcecode.sh [--desktop-entry] [--tablet]
```
`--desktop-entry` creates a Desktop icon + application menu entry; without it, only
`run_map_db_cache.sh` is generated. Any other flag (e.g. `--tablet`) is passed through
to the app on every launch.

### Run
```
./run_map_db_cache.sh
```
or manually:
```
source .venv/bin/activate
python app.py [--silent] [--verbose] [--minimize] [--tablet]
```

### Preview downloaded map
```
python preview.py [path_to_file] (DEFAULT='map/map.mbtiles')
```

### Build executable
script for building the executable for Linux is missing now

## Windows
Contours on the elevation layer are not yet supported on Windows. Python + GDAL
(via OSGeo4W) are already vendored in the project — run all commands below from
the project root directory.
```
set PYTHON_EXE=%CD%\gdal_runner\gdal_win\OSGeo4W\bin\python.exe
set PYTHONHOME=%CD%\gdal_runner\gdal_win\Python312
```

### Run
```
%PYTHON_EXE% app.py [--silent] [--verbose] [--minimize] [--tablet]
```

### Preview downloaded map
```
%PYTHON_EXE% preview.py [path_to_file] (DEFAULT='map/map.mbtiles')
```

### Build executable
```
build.bat
```
