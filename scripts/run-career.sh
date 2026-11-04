#!/bin/sh
set -eu
CAREER_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$CAREER_ROOT"
if [ ! -x "$CAREER_ROOT/.venv/bin/python3" ]; then
    echo "请先在 $CAREER_ROOT 运行 uv sync --dev。" >&2
    exit 1
fi
exec "$CAREER_ROOT/.venv/bin/python3" -m drugstory.career.server \
    --port 8883 --save-path "$CAREER_ROOT/saves/development-autosave.json" "$@"
