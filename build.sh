#!/bin/bash

echo "Installing Python requirements..."
pip install pyinstaller==5.13.2
echo "Building executable file..."
python -m PyInstaller --onefile --name MapDbCache -i icon.ico --noconsole --add-data "png:png" --add-data ".venv/lib/python3.11/site-packages/kivy_garden/mapview/icons:kivy_garden/mapview/icons" main.py
mv dist/MapDbCache MapDbCache
echo "Removing building artifacts..."
rm -r build dist
echo "Usage: ./MapDbCache"
