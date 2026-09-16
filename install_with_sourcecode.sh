#!/bin/bash

# Stop on error
set -e

# Define paths
SCRIPT_NAME="app.py"
LAUNCHER_NAME="run_map_db_cache.sh"
APP_PATH="$(realpath .)"
ICON_PATH=$APP_PATH/png/icon.png
DESKTOP_FILE="$HOME/Desktop/MapDbCache.desktop"
APPLICATIONS_DESKTOP_FILE="$HOME/.local/share/applications/MapDbCache.desktop"

TABLET_FLAG=""
for arg in "$@"; do
    if [ "$arg" = "--tablet" ]; then
        TABLET_FLAG="--tablet"
    fi
done

echo "Installing Python requirements..."
if [ -f requirements.txt ]; then
    python3 -m venv .venv
    . .venv/bin/activate
    pip install -r requirements.txt
    python3 patch_mapview.py
    pip install "numpy>1.0.0" wheel "setuptools>=67"
    pip install gdal[numpy]=="$(gdal-config --version).*"
else
    echo "requirements.txt not found."
    exit 1
fi

echo "Creating launcher script: $LAUNCHER_NAME"
cat <<EOF > $LAUNCHER_NAME
#!/bin/bash
# Usage: ./run_map_db_cache.sh
source $APP_PATH/.venv/bin/activate
export SDL_VIDEO_X11_WMCLASS=MapDbCache
export SDL_APP_ID=MapDbCache
python3 "$APP_PATH/$SCRIPT_NAME" $TABLET_FLAG "\$@"
EOF

chmod 755 $LAUNCHER_NAME

echo "Creating desktop shortcut at $DESKTOP_FILE"
cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Version=1.0
Type=Application
Name=MapDbCache
Exec=bash -c "cd $APP_PATH && ./$LAUNCHER_NAME"
Icon=$ICON_PATH
Terminal=false
Categories=Utility;
StartupWMClass=MapDbCache
EOF

# Make it executable
chmod 755 "$DESKTOP_FILE"

echo "Desktop shortcut created: $DESKTOP_FILE"
echo "Double-click it on your desktop to run."

echo "Registering application at $APPLICATIONS_DESKTOP_FILE"
mkdir -p "$(dirname "$APPLICATIONS_DESKTOP_FILE")"
cp "$DESKTOP_FILE" "$APPLICATIONS_DESKTOP_FILE"
chmod 755 "$APPLICATIONS_DESKTOP_FILE"
