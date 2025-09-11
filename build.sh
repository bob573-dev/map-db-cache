#!/bin/bash

echo "Installing Python requirements..."
pip install pyinstaller==5.13.2
echo "Building executable file..."
python -m PyInstaller MapDbCache_linux.spec
mv dist/MapDbCache MapDbCache
echo "Removing building artifacts..."
rm -r build dist
echo "Usage: ./MapDbCache"
