#!/bin/bash

# Stop on error
set -e

# Define paths
SCRIPT_NAME="main.py"
LAUNCHER_NAME="run_map_db_cache.sh"
APP_PATH="$(realpath .)"
ICON_PATH=$APP_PATH/png/icon.png
DESKTOP_FILE="$HOME/Desktop/MapDbCache.desktop"

echo "Installing Python requirements..."
if [ -f requirements.txt ]; then
    python3 -m venv .venv
    . .venv/bin/activate
    pip install -r requirements.txt
    python3 patch_mapview.py
else
    echo "requirements.txt not found."
    exit 1
fi

echo "Creating launcher script: $LAUNCHER_NAME"
cat <<EOF > $LAUNCHER_NAME
#!/bin/bash
# Usage: ./run_map_db_cache.sh
source $APP_PATH/.venv/bin/activate
python3 "$APP_PATH/$SCRIPT_NAME" --maximize "\$@"
EOF

chmod 777 $LAUNCHER_NAME

echo "Creating desktop shortcut at $DESKTOP_FILE"
cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Version=1.0
Type=Application
Name=MapDbCache
Exec=bash -c "cd $APP_PATH && ./$LAUNCHER_NAME"
Icon=$ICON_PATH
Terminal=true
Categories=Utility;
EOF

# Make it executable
chmod 755 "$DESKTOP_FILE"

echo "Desktop shortcut created: $DESKTOP_FILE"
echo "Double-click it on your desktop to run."
