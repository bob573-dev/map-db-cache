# MapDbCache

## Linux
### Requirements
python >= 3.11.11 \
SWIG (4 or greater) \
libgdal (3.12.1 or greater) \
numpy (1.0.0 or greater) \
setuptools (python) \
wheel (python)

### Manual installation
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python patch_mapview.py
pip install numpy>1.0.0 wheel setuptools>=67
pip install gdal[numpy]=="$(gdal-config --version).*"
```

then check gdal installation
```
python3 -c 'from osgeo import gdal_array'
```

If this command raises an ImportError, numpy-based raster support has not been properly installed:
```
pip install --no-cache --force-reinstall gdal[numpy]=="$(gdal-config --version).*"
```

if you have another problems - read more about installing gdal python package here \
https://pypi.org/project/GDAL/

### Installation with script
may have problems
```
sh install_with_sourcecode.sh
```

### Run
```
python main.py [--silent] [--verbose] [--minimize]
```

### Preview downloaded map
```
python preview.py [path_to_file] (DEFAULT='map/map.mbtiles')
```

### Build executable
script for building the executable for Linux is missing now

## Windows
contours on elevation layer are missing in Windows version now.

python with all dependencies is already configured inside the project

OSGeo4W was used for gdal installation

### Run
run all commands from project root directory. \
set path to project python and its libs
```
set PYTHON_EXE=%CD%\gdal_runner\gdal_win\OSGeo4W\bin\python.exe
set PYTHONHOME=%CD%\gdal_runner\gdal_win\Python312
```
run
```
%PYTHON_EXE% main.py [--silent] [--verbose] [--minimize]
```

### Preview downloaded map
run all commands from project root directory. \
set path to project python and its libs
```
set PYTHON_EXE=%CD%\gdal_runner\gdal_win\OSGeo4W\bin\python.exe
set PYTHONHOME=%CD%\gdal_runner\gdal_win\Python312
```
run
```
%PYTHON_EXE% preview.py [path_to_file] (DEFAULT='map/map.mbtiles')
```

### Build executable
```
build.bat
```
