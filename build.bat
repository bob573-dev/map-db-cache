@echo off
echo Installing Python requirements...
pip install pyinstaller==5.13.2

echo Building executable file...
python -m PyInstaller ^
    --onefile ^
    --name MapDbCache ^
    -i icon.ico ^
    --noconsole ^
    --hidden-import=win32timezone ^
    --add-data "png;png" ^
    --add-data ".venv\Lib\site-packages\kivy_garden\mapview\icons;kivy_garden/mapview/icons" ^
    main.py

move dist\MapDbCache.exe MapDbCache.exe
echo Removing build artifacts...
rmdir /s /q build
rmdir /s /q dist

echo Usage: MapDbCache.exe