#!/usr/bin/env bash
set -e
set -o pipefail
RED="\e[31m"
YELLOW="\e[33m"
RESET="\e[0m"

source ../.venv/bin/activate

PYTHON_BIN="${PYTHON_BIN:-python3}"

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
# 2. Collect shared library dependencies
# --------------------------------------
# Never bundle glibc/loader/NSS libraries. They are tightly coupled to the exact
# libc build already running the process (GLIBC_PRIVATE symbols, NSS module ABI,
# /etc/nsswitch.conf lookups); pointing LD_LIBRARY_PATH at a different libc.so.6
# breaks every command run with that env, not just GDAL, e.g.:
#   symbol lookup error: .../lib/libc.so.6: undefined symbol: __nptl_change_stack_perm,
#   version GLIBC_PRIVATE
# These always come from (and must match) the host system.
EXCLUDE_LIB_REGEX='^(libc|libm|libpthread|libdl|librt|libresolv|libutil|libcrypt|libnss_|ld-linux)'

echo "Collecting shared libraries..."

for BIN in "$BIN_DIR"/*; do
    echo "  → $BIN"
    ldd "$BIN" | awk '/=>/ {print $3}' | while read -r LIB; do
        LIB_NAME="$(basename "$LIB")"
        if [[ -f "$LIB" ]] && [[ ! "$LIB_NAME" =~ $EXCLUDE_LIB_REGEX ]]; then
            cp --update=none "$LIB" "$LIB_DIR/" || true
        fi
    done || true
done

echo "Libraries collected."

# --------------------------------------
# 3. GDAL data
# --------------------------------------
if [ -d "/usr/share/gdal" ]; then
    cp -r /usr/share/gdal "$DATA_DIR/"
elif [ -d "/usr/share/gdal3" ]; then
    cp -r /usr/share/gdal3 "$DATA_DIR/gdal"
else
    echo -e "${RED}WARNING:${RESET} GDAL data directory not found"
fi

# --------------------------------------
# 4. GDAL driver plugins
# --------------------------------------
GDAL_PLUGIN_CANDIDATES=(
    /usr/lib/gdalplugins
    /usr/lib/x86_64-linux-gnu/gdalplugins
    /usr/lib64/gdalplugins
)
GDAL_PLUGIN_DIR=""
for candidate in "${GDAL_PLUGIN_CANDIDATES[@]}"; do
    if [ -d "$candidate" ]; then
        GDAL_PLUGIN_DIR="$candidate"
        break
    fi
done

if [ -n "$GDAL_PLUGIN_DIR" ]; then
    cp -r "$GDAL_PLUGIN_DIR" "$DATA_DIR/gdalplugins"
    for plugin in "$DATA_DIR/gdalplugins"/*; do
        [ -f "$plugin" ] || continue
        ldd "$plugin" 2>/dev/null | awk '/=>/ {print $3}' | while read -r LIB; do
            LIB_NAME="$(basename "$LIB")"
            if [[ -f "$LIB" ]] && [[ ! "$LIB_NAME" =~ $EXCLUDE_LIB_REGEX ]]; then
                cp --update=none "$LIB" "$LIB_DIR/" || true
            fi
        done || true
    done
else
    echo -e "${YELLOW}NOTE:${RESET} no GDAL driver-plugin directory found — assuming this GDAL build has no plugin drivers"
    mkdir -p "$DATA_DIR/gdalplugins"
fi

# --------------------------------------
# 5. PROJ data
# --------------------------------------
if [ -d "/usr/share/proj" ]; then
    cp -r /usr/share/proj "$DATA_DIR/"
    find "$DATA_DIR/proj" -type f \( -iname '*.gsb' -o -iname '*.gtx' -o -iname '*.tif' \) -delete
else
    echo -e "${RED}WARNING:${RESET} PROJ data directory not found"
fi

# --------------------------------------
# 6. Make the bundle relocatable: patch RPATH instead of relying on
#    LD_LIBRARY_PATH (avoids leaking the bundle's libs into the whole process).
# --------------------------------------
if ! command -v patchelf >/dev/null 2>&1; then
    echo -e "${RED}ERROR:${RESET} patchelf is required to make the bundle relocatable but was not found."
    echo "Install it first, e.g.: sudo pacman -S patchelf   |   sudo apt install patchelf"
    exit 1
fi

echo "Patching RPATH on collected binaries/libraries..."
for BIN in "$BIN_DIR"/*; do
    patchelf --set-rpath '$ORIGIN/../lib' "$BIN" 2>/dev/null || true
done
for LIB in "$LIB_DIR"/*; do
    patchelf --set-rpath '$ORIGIN' "$LIB" 2>/dev/null || true
done
for plugin in "$DATA_DIR/gdalplugins"/*; do
    [ -f "$plugin" ] && patchelf --set-rpath '$ORIGIN/../../lib' "$plugin" 2>/dev/null || true
done

# --------------------------------------
# 8. osgeo Python bindings, installed + RPATH-patched straight into gdal_linux/pylib
# --------------------------------------
# Note: on Debian/Ubuntu, gdal-config ships in a separate "-dev" package (libgdal-dev) from
# the CLI tools (gdal-bin) collected above, so it can legitimately be missing even though step
# 1 succeeded — that's not fatal to the rest of the bundle, just to this step.
PYLIB_DIR="$OUT_DIR/pylib"
if ! command -v gdal-config >/dev/null 2>&1; then
    echo -e "${YELLOW}NOTE:${RESET} gdal-config not found — skipping osgeo Python bindings."
    echo "Install your distro's GDAL dev package (e.g. libgdal-dev / gdal-devel) to enable it."
else
    echo "Installing GDAL Python bindings with $PYTHON_BIN into $PYLIB_DIR..."
    mkdir -p "$PYLIB_DIR"
    "$PYTHON_BIN" -m pip install -q "numpy>1.0.0" wheel "setuptools>=67"
    if "$PYTHON_BIN" -m pip install --no-build-isolation --no-cache-dir --target "$PYLIB_DIR" "gdal[numpy]==$(gdal-config --version).*"; then

        echo "Patching RPATH on $PYLIB_DIR/osgeo/*.so..."
        find "$PYLIB_DIR/osgeo" -maxdepth 1 -name '*.so' | while read -r SO; do
            SO_DIR="$(dirname "$SO")"
            REL_LIB="$(realpath --relative-to="$SO_DIR" "$LIB_DIR")" || continue
            patchelf --set-rpath "\$ORIGIN/$REL_LIB" "$SO" 2>/dev/null || true
        done || true

        # numpy/f2py and numpy/testing must NOT be pruned, despite nothing in this repo
        # statically importing them: gdal_calc.py's Calc() builds its --calc eval namespace
        # with `{key: getattr(module, key) for module in [gdal_array, numpy] for key in
        # dir(module) if not key.startswith('__')}` -- this unconditionally touches every
        # public numpy attribute, including f2py/testing, which numpy only exposes via a lazy
        # `__getattr__` import. Deleting those directories doesn't remove them from dir(numpy),
        # so gdal_calc.py crashes with ModuleNotFoundError the moment it runs (found live, on a
        # packaged Steam Deck build: hillshade/color-relief generation failing on every run).
        # numpy/distutils is safe to remove -- numpy's own __dir__() explicitly excludes it
        # (along with matlib/matrixlib/tests/conftest/version/array_api) from dir(numpy), so
        # this same getattr(module, key) loop never reaches it.
        echo "Pruning unused numpy test/build-tooling files from $PYLIB_DIR..."
        find "$PYLIB_DIR/numpy" -type d -name 'tests' -exec rm -rf {} + 2>/dev/null || true
        rm -rf "$PYLIB_DIR/numpy/distutils"
        find "$PYLIB_DIR/numpy" -name '*.pyi' -delete
    else
        echo -e "${RED}WARNING:${RESET} installing GDAL Python bindings into $PYLIB_DIR failed — continuing without it."
        rm -rf "$PYLIB_DIR"
    fi
fi

# --------------------------------------
# 9. Bundle metadata
# --------------------------------------
{
    echo "built_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "arch=$(uname -m)"
    if [ -f /etc/os-release ]; then
        # shellcheck disable=SC1091
        source /etc/os-release
        echo "distro=${NAME:-unknown}"
        echo "distro_version=${VERSION_ID:-unknown}"
    else
        echo "distro=unknown"
        echo "distro_version=unknown"
    fi
    echo "gdal_version=$(gdal-config --version 2>/dev/null || echo unknown)"
    echo "glibc_version=$(ldd --version | head -1 | grep -oE '[0-9]+\.[0-9]+$' || echo unknown)"
    echo "python_version=$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo unknown)"
} > "$OUT_DIR/BUNDLE_INFO"

echo ""
echo "GDAL Linux bundle built successfully → $OUT_DIR"
echo "This bundle is only valid for: $(cat "$OUT_DIR/BUNDLE_INFO" | tr '\n' ' ')"
