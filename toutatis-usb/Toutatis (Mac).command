#!/usr/bin/env bash
# Double-clickable launcher for macOS (Finder opens .command files in Terminal).
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/toutatis.sh" "$@"
