#!/bin/sh
set -eu
NEXT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$NEXT_ROOT"
if [ ! -x "$NEXT_ROOT/.venv/bin/python3" ]; then
    echo "请先在 $NEXT_ROOT 运行 uv sync --dev。" >&2
    exit 1
fi
exec "$NEXT_ROOT/.venv/bin/python3" -m drugstory.ui.web_server     --port 8878 --save-path "$NEXT_ROOT/saves/next-autosave.json" "$@"
