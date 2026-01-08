@echo off
setlocal

set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%
set PYTHONHOME=%SCRIPT_DIR%\gdal_runner\gdal_win\Python312
set PYTHON_EXE=%SCRIPT_DIR%\gdal_runner\gdal_win\OSGeo4W\bin\python.exe

echo Using Python: "%PYTHON_EXE%"

echo Installing Python requirements...
"%PYTHON_EXE%" -m pip install pyinstaller==5.13.2

echo Building executable file...
"%PYTHON_EXE%" -m PyInstaller MapDbCache_win.spec

move dist\MapDbCache.exe MapDbCache.exe

echo Removing build artifacts...
rmdir /s /q build
rmdir /s /q dist

echo Usage: MapDbCache.exe
