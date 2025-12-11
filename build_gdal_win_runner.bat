@echo off
echo Installing Python requirements...
pip install pyinstaller==5.13.2

echo "Building executable file..."
python -m PyInstaller gdal_win_runner.spec

move dist\gdal_win_runner.exe gdal_win_runner.exe
echo Removing build artifacts...
rmdir /s /q build
rmdir /s /q dist

echo "Usage: gdal_win_runner.exe <gdal_command> [args...]"