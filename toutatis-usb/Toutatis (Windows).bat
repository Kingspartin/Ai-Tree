@echo off
REM ============================================================
REM  Toutatis - portable launcher for Windows
REM  Double-click this file to run. No installation needed.
REM ============================================================
setlocal
cd /d "%~dp0"

REM Find a Python 3 interpreter.
set "PYEXE="
where py >nul 2>&1 && set "PYEXE=py -3"
if not defined PYEXE (
  where python >nul 2>&1 && set "PYEXE=python"
)

if not defined PYEXE (
  echo.
  echo [!] Python 3 was not found on this computer.
  echo     Install it from https://www.python.org/downloads/
  echo     During install, tick "Add Python to PATH", then run this again.
  echo.
  pause
  exit /b 1
)

%PYEXE% "%~dp0toutatis_portable.py" %*
