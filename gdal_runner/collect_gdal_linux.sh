#!/usr/bin/env bash
set -e

OUT_DIR="gdal_linux"
BIN_DIR="$OUT_DIR/bin"
LIB_DIR="$OUT_DIR/lib"
DATA_DIR="$OUT_DIR/data"

echo "Cleaning previous bundle..."
rm -rf "$OUT_DIR"
mkdir -p "$BIN_DIR" "$LIB_DIR" "$DATA_DIR"

# ---- 1. Locate binaries ----
which gdal_translate >/dev/null
which gdalbuildvrt >/dev/null

cp "$(which gdal_translate)" "$BIN_DIR/"
cp "$(which gdalbuildvrt)" "$BIN_DIR/"

echo "Copied gdal executables."

# ---- 2. Copy library dependencies ----
for BIN in "$BIN_DIR"/*; do
    echo "Collecting libs for $BIN..."
    ldd "$BIN" | awk '/=>/ {print $3}' | while read -r LIB; do
        if [[ -f "$LIB" ]]; then
            cp -n "$LIB" "$LIB_DIR/" || true
        fi
    done
done

echo "Libraries collected."

# ---- 3. GDAL data ----
if [ -d "/usr/share/gdal" ]; then
    cp -r /usr/share/gdal "$DATA_DIR/"
fi

# ---- 4. PROJ data ----
if [ -d "/usr/share/proj" ]; then
    cp -r /usr/share/proj "$DATA_DIR/"
fi

echo "GDAL Linux bundle built → $OUT_DIR"
