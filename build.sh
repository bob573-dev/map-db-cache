#!/bin/bash

# Every argument passed to this script is added to sys.argv before app.py runs
# inside the packaged executable, e.g.: ./build.sh --tablet --minimize
# Any number of arguments works, not just one. This is unconditional — whatever
# is passed here always gets added on every launch, it's not a fallback default.
HOOK_FILE="linux_runtime_args_hook.py"
ARGS_LITERAL=$(python3 -c "import json, sys; print(json.dumps(sys.argv[1:]))" "$@")
cat > "$HOOK_FILE" <<EOF
import sys

sys.argv.extend($ARGS_LITERAL)
EOF

source .venv/bin/activate

echo "Installing Python requirements..."
pip install pyinstaller
echo "Building executable file..."
python -m PyInstaller MapDbCache_linux.spec
mv dist/MapDbCache MapDbCache
echo "Removing building artifacts..."
rm -r build dist
echo "Usage: ./MapDbCache"
