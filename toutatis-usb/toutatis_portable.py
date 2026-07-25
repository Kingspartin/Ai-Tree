#!/usr/bin/env python3
"""
Toutatis — Portable USB launcher
================================

This is a self-contained wrapper around megadose's Toutatis
(https://github.com/megadose/toutatis). It lets the tool run straight from a
USB stick on Windows, macOS, or Linux without a system-wide install.

On first run it installs the bundled dependencies (found in ./vendor/wheels)
into a local ./libs folder next to this script — nothing is written to the
host computer and no internet connection is required. Later runs reuse ./libs.

Usage
-----
  Double-click a launcher (Windows .bat / Mac .command / Linux toutatis.sh)
  to get a guided, interactive prompt.

  Or from a terminal, classic Toutatis flags still work:
      python toutatis_portable.py -u <username> -s <sessionid>
      python toutatis_portable.py -i <instagram_id> -s <sessionid>
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LIBS = os.path.join(ROOT, "libs")
APP = os.path.join(ROOT, "app")
WHEELS = os.path.join(ROOT, "vendor", "wheels")
REQUIREMENTS = os.path.join(ROOT, "requirements.txt")

# Bundled Toutatis source and the local dependency folder must be importable.
for path in (APP, LIBS):
    if path not in sys.path:
        sys.path.insert(0, path)

REQUIRED_MODULES = ("requests", "phonenumbers", "pycountry")


def _deps_available():
    import importlib.util

    return all(importlib.util.find_spec(m) is not None for m in REQUIRED_MODULES)


def _pip_install(online):
    """Install requirements into ./libs. Offline (bundled wheels) by default."""
    cmd = [sys.executable, "-m", "pip", "install", "--target", LIBS,
           "--disable-pip-version-check", "-r", REQUIREMENTS]
    if not online:
        cmd += ["--no-index", "--find-links", WHEELS]
    return subprocess.call(cmd)


def ensure_dependencies():
    # Frozen (PyInstaller .exe/binary): dependencies are baked in — nothing to do.
    if getattr(sys, "frozen", False):
        return True
    if _deps_available():
        return True

    os.makedirs(LIBS, exist_ok=True)
    print("First run: setting up bundled dependencies (this happens once)...\n")

    # Prefer the offline wheels shipped on the USB.
    if os.path.isdir(WHEELS) and os.listdir(WHEELS) and _pip_install(online=False) == 0:
        pass
    else:
        # Fall back to downloading from PyPI if the bundled wheels can't be used
        # (e.g. an unusual Python version with no matching wheel).
        print("\nBundled install unavailable — trying to fetch from the internet...\n")
        if _pip_install(online=True) != 0:
            print("\n[!] Could not install the required Python packages "
                  "(requests, phonenumbers, pycountry).")
            print("    Make sure Python 3 includes pip, or connect to the internet "
                  "and run this again.")
            return False

    # Re-scan sys.path now that packages exist in ./libs.
    import importlib
    importlib.invalidate_caches()
    return _deps_available()


def interactive():
    print("=" * 52)
    print("  TOUTATIS  —  Instagram OSINT (portable USB edition)")
    print("=" * 52)
    print("\nYou need your own Instagram 'sessionid' cookie.")
    print("How to get it: log in to instagram.com in a browser, open the")
    print("browser dev tools -> Application/Storage -> Cookies -> copy the")
    print("value of the 'sessionid' cookie.\n")

    session_id = input("Instagram sessionid : ").strip()
    if not session_id:
        print("\nNo sessionid entered — cannot continue.")
        return 1

    print("\nSearch by:")
    print("  [1] username  (default)")
    print("  [2] Instagram numeric ID")
    choice = input("Choice [1/2] : ").strip() or "1"

    if choice == "2":
        target = input("Instagram ID : ").strip()
        flag = "-i"
    else:
        target = input("Username     : ").strip().lstrip("@")
        flag = "-u"

    if not target:
        print("\nNothing to look up.")
        return 1

    print("\nLooking up...\n" + "-" * 52)
    sys.argv = ["toutatis", flag, target, "-s", session_id]
    return _run_core()


def _run_core():
    from toutatis import core
    try:
        core.main()
        return 0
    except SystemExit as exc:  # argparse / the tool call exit()
        code = exc.code
        if isinstance(code, str):
            print(code)
            return 1
        return int(code or 0)
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 1
    except Exception as exc:  # noqa: BLE001 - keep the USB UX friendly
        name = type(exc).__name__
        if "Connection" in name or "Proxy" in name or "Timeout" in name or "SSL" in name:
            print("\n[!] Could not reach Instagram. Check your internet "
                  "connection and try again.")
        else:
            print(f"\n[!] Something went wrong ({name}): {exc}")
            print("    Instagram may have changed its API, your sessionid may "
                  "be expired, or you may be rate-limited. Try again later.")
        return 1


def main():
    if not ensure_dependencies():
        _pause()
        return 1

    # If real CLI flags were passed, behave exactly like classic Toutatis.
    if len(sys.argv) > 1:
        return _run_core()

    # No arguments (e.g. double-clicked) -> friendly guided mode.
    rc = interactive()
    _pause()
    return rc


def _pause():
    # Keep the window open when launched by double-click.
    try:
        input("\nDone. Press Enter to close.")
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    sys.exit(main())
