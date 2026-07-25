#!/usr/bin/env bash
# ============================================================
#  Toutatis - portable launcher for Linux and macOS
#  Run:  ./toutatis.sh          (guided prompt)
#    or: ./toutatis.sh -u name -s <sessionid>
# ============================================================
set -euo pipefail

# Resolve the folder this script lives in (works when run from anywhere).
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Find a Python 3 interpreter.
PYEXE=""
if command -v python3 >/dev/null 2>&1; then
  PYEXE="python3"
elif command -v python >/dev/null 2>&1 && python -c 'import sys; sys.exit(0 if sys.version_info[0]==3 else 1)' 2>/dev/null; then
  PYEXE="python"
fi

if [ -z "$PYEXE" ]; then
  echo
  echo "[!] Python 3 was not found on this computer."
  echo "    macOS:  install from https://www.python.org/downloads/  (or: brew install python)"
  echo "    Linux:  sudo apt install python3 python3-pip   (or your distro's equivalent)"
  echo
  exit 1
fi

exec "$PYEXE" "$DIR/toutatis_portable.py" "$@"
