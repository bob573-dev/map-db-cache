python 3.11.11

## Installation with desktop shortcut
sh install_with_source.sh
# or
sh install_with_onefile.sh

## Manual installation
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python patch_mapview.py

## Run
python main.py [--silent] [--verbose] [--maximize]

## Preview downloaded map
python preview.py [path_to_file] (DEFAULT='map/map.mbtiles')

## Build executable
# linux
sh build.sh
