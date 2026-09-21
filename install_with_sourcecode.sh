#!/bin/bash

# Stop on error
set -e

# Define paths
SCRIPT_NAME="app.py"
LAUNCHER_NAME="run_map_db_cache.sh"
APP_PATH="$(realpath .)"
ICON_PATH=$APP_PATH/png/icon.png
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
DESKTOP_FILE="$DESKTOP_DIR/MapDbCache.desktop"
APPLICATIONS_DESKTOP_FILE="$HOME/.local/share/applications/MapDbCache.desktop"

CREATE_DESKTOP_ENTRY=0
APP_ARGS=()
for arg in "$@"; do
    if [ "$arg" = "--desktop-entry" ]; then
        CREATE_DESKTOP_ENTRY=1
    else
        APP_ARGS+=("$arg")
    fi
done

BAKED_ARGS=""
[ ${#APP_ARGS[@]} -gt 0 ] && BAKED_ARGS="$(printf '%q ' "${APP_ARGS[@]}")"

echo "Checking build dependencies..."

GDAL_CLI_TOOLS="gdal_translate gdalbuildvrt gdalwarp gdaldem gdal_contour gdal_rasterize ogr2ogr"
for tool in $GDAL_CLI_TOOLS; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: $tool not found. Install your distro's GDAL CLI package (e.g. gdal-bin / gdal)."
        exit 1
    }
done

command -v gdal-config >/dev/null 2>&1 || {
    echo "ERROR: gdal-config not found. Install your distro's GDAL dev package (e.g. libgdal-dev / gdal-devel)."
    exit 1
}

echo "Installing Python requirements..."
if [ -f requirements.txt ]; then
    python3 -m venv .venv
    . .venv/bin/activate
    pip install -r requirements.txt
    python3 patch_mapview.py
    pip install "numpy>1.0.0" wheel "setuptools>=67"
    pip install gdal[numpy]=="$(gdal-config --version).*"

    if ! python3 -c 'from osgeo import gdal_array' 2>/dev/null; then
        echo "gdal_array import failed -- retrying with --force-reinstall..."
        pip install --no-cache --force-reinstall gdal[numpy]=="$(gdal-config --version).*"
        python3 -c 'from osgeo import gdal_array' || {
            echo "ERROR: numpy-based raster support still not working. See https://pypi.org/project/GDAL/"
            exit 1
        }
    fi
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
python3 "$APP_PATH/$SCRIPT_NAME" $BAKED_ARGS"\$@"
EOF

chmod 755 $LAUNCHER_NAME

if [ "$CREATE_DESKTOP_ENTRY" -eq 1 ]; then
    echo "Creating desktop shortcut at $DESKTOP_FILE"
    mkdir -p "$DESKTOP_DIR"
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

    # Nautilus (GNOME Files) treats a fresh Desktop launcher as untrusted until it also carries
    # the `metadata::trusted` GIO attribute (normally set via right-click -> "Allow Launching") --
    # same fix as tools/desktop_shortcut.py:_mark_trusted for the packaged build. Best-effort,
    # backgrounded so a slow/missing `gio` doesn't hold up the rest of this script.
    command -v gio >/dev/null 2>&1 && (gio set -t string "$DESKTOP_FILE" metadata::trusted true &)

    echo "Registering application at $APPLICATIONS_DESKTOP_FILE"
    mkdir -p "$(dirname "$APPLICATIONS_DESKTOP_FILE")"
    cp "$DESKTOP_FILE" "$APPLICATIONS_DESKTOP_FILE"
    chmod 755 "$APPLICATIONS_DESKTOP_FILE"

    echo "Desktop shortcut created: $DESKTOP_FILE"
    echo "Double-click it on your desktop to run."
else
    echo "Skipping desktop shortcut creation (pass --desktop-entry to create one)."
    echo "Run ./$LAUNCHER_NAME to start the app."
fi
echo "App will be launched with arguments: ${BAKED_ARGS:-<none>}"

