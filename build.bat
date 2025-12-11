@echo off
echo Installing Python requirements...
pip install pyinstaller==5.13.2

echo "Building executable file..."
python -m PyInstaller MapDbCache_win.spec --onefile

move dist\MapDbCache.exe MapDbCache.exe
echo Removing build artifacts...
rmdir /s /q build
rmdir /s /q dist

echo "Usage: MapDbCache.exe"