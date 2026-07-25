# Toutatis — Portable USB Edition

A self-contained, run-from-USB packaging of
[megadose/toutatis](https://github.com/megadose/toutatis), an OSINT tool that
extracts information from Instagram accounts (username, full name, follower
counts, public email/phone where exposed, and obfuscated email/phone hints)
using **your own** Instagram `sessionid`.

The goal of this folder: **copy it to a USB stick, plug into any computer with
Python 3, double-click a launcher — done.** No system install, and the
dependencies install offline from bundled wheels.

## Quick start

1. Copy this whole folder to a USB drive.
2. On the target computer (needs Python 3 — https://www.python.org/downloads/):
   - **Windows:** double-click `Toutatis (Windows).bat`
   - **macOS:** double-click `Toutatis (Mac).command`
   - **Linux:** `./toutatis.sh`
3. First run sets up bundled dependencies (offline, once). Then answer the
   prompts: paste your Instagram `sessionid` and a username to look up.

See `START-HERE.txt` for the non-technical, step-by-step version, including
how to grab your `sessionid` cookie.

## Command-line (unchanged from upstream)

```bash
python toutatis_portable.py -u <username>    -s <sessionid>
python toutatis_portable.py -i <instagramID> -s <sessionid>
```

## How it's laid out

```
toutatis-usb/
├── START-HERE.txt              Plain-English instructions
├── Toutatis (Windows).bat      Double-click launcher (Windows)
├── Toutatis (Mac).command      Double-click launcher (macOS)
├── toutatis.sh                 Launcher (Linux/macOS terminal)
├── toutatis_portable.py        Bootstrapper: sets up deps + guided/CLI run
├── requirements.txt            requests, phonenumbers, pycountry
├── app/toutatis/               Vendored upstream source (core.py, __init__.py)
├── vendor/wheels/              Offline dependency wheels (Win/macOS/Linux)
├── libs/                       Auto-created on first run (git-ignored)
└── LICENSE                     GPL-3.0 (upstream license)
```

### Why it works offline and cross-platform

`vendor/wheels/` ships the pure-Python dependencies (universal wheels) plus
`charset-normalizer` binaries for Windows, macOS (universal2), and Linux
(x86_64 + aarch64), with a `py3-none-any` fallback for any other Python.
On first run, `toutatis_portable.py` installs them into a local `libs/` folder
with `pip install --target` — nothing touches the host system, and no internet
is required. If the bundled wheels don't fit an unusual Python, it falls back
to fetching from PyPI.

## Requirements on the host

- **Python 3** with `pip` (standard in official installers). The launchers
  detect Python and print install guidance if it's missing.

## Legal / responsible use

This tool queries Instagram's own API with your own authenticated session.
Only use it against accounts and in contexts where you are authorized to do so,
and in compliance with Instagram's Terms of Service and applicable law.
Licensed under GPL-3.0 (see `LICENSE`). Upstream:
https://github.com/megadose/toutatis
