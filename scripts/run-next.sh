#!/bin/sh
# Compatibility alias within v0.4; never starts the v0.3 port.
set -eu
exec "$(dirname -- "$0")/run-career.sh" "$@"
