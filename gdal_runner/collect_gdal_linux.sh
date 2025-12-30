#!/usr/bin/env bash
set -e
RED="\e[31m"
RESET="\e[0m"

OUT_DIR="gdal_linux"
BIN_DIR="$OUT_DIR/bin"
LIB_DIR="$OUT_DIR/lib"
DATA_DIR="$OUT_DIR/data"

echo "Cleaning previous bundle..."
rm -rf "$OUT_DIR"
mkdir -p "$BIN_DIR" "$LIB_DIR" "$DATA_DIR"

# --------------------------------------
# 1. GDAL / OGR executables
# --------------------------------------
EXECUTABLES=(
    gdal_translate
    gdalbuildvrt
    gdalwarp
    gdaldem
    gdal_contour
    gdal_rasterize
    ogr2ogr
)

echo "Locating GDAL/OGR executables..."
for exe in "${EXECUTABLES[@]}"; do
    if ! command -v "$exe" >/dev/null 2>&1; then
        echo "ERROR: $exe not found"
        exit 1
    fi
    cp "$(command -v "$exe")" "$BIN_DIR/"
done

echo "Copied GDAL/OGR executables."

# --------------------------------------
# 2. GDAL Python utilities
# --------------------------------------
PY_SCRIPTS=(
    gdal_calc.py
    gdal2tiles.py
)

echo "Locating GDAL Python scripts..."
for py in "${PY_SCRIPTS[@]}"; do
    if command -v "$py" >/dev/null 2>&1; then
        cp "$(command -v "$py")" "$BIN_DIR/"
    elif [ -f "/usr/bin/$py" ]; then
        cp "/usr/bin/$py" "$BIN_DIR/"
    else
        echo -e "${RED}WARNING:${RESET} $py not found"
    fi
done

# --------------------------------------
# 3. Collect shared library dependencies
# --------------------------------------
echo "Collecting shared libraries..."

for BIN in "$BIN_DIR"/*; do
    echo "  → $BIN"
    ldd "$BIN" | awk '/=>/ {print $3}' | while read -r LIB; do
        if [[ -f "$LIB" ]]; then
            cp --update=none "$LIB" "$LIB_DIR/" || true
        fi
    done
done

echo "Libraries collected."

# --------------------------------------
# 4. GDAL data
# --------------------------------------
if [ -d "/usr/share/gdal" ]; then
    cp -r /usr/share/gdal "$DATA_DIR/"
elif [ -d "/usr/share/gdal3" ]; then
    cp -r /usr/share/gdal3 "$DATA_DIR/gdal"
else
    echo "${RED}WARNING:${RESET} GDAL data directory not found"
fi

# --------------------------------------
# 5. PROJ data
# --------------------------------------
if [ -d "/usr/share/proj" ]; then
    cp -r /usr/share/proj "$DATA_DIR/"
else
    echo "${RED}WARNING:${RESET} PROJ data directory not found"
fi

echo ""
echo "GDAL Linux bundle built successfully → $OUT_DIR"
