@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "BOOTSTRAP_PYTHON="
where py >nul 2>nul
if not errorlevel 1 set "BOOTSTRAP_PYTHON=py -3"

if not defined BOOTSTRAP_PYTHON (
    where python >nul 2>nul
    if not errorlevel 1 set "BOOTSTRAP_PYTHON=python"
)

if not defined BOOTSTRAP_PYTHON (
    echo [xray-prism] Python 3 not found. Please install Python 3.10+ first.
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [xray-prism] Creating virtual environment...
    call %BOOTSTRAP_PYTHON% -m venv .venv
    if errorlevel 1 exit /b 1
)

".venv\Scripts\python.exe" -c "import fastapi,uvicorn,requests,yaml,dotenv" >nul 2>nul
if errorlevel 1 (
    echo [xray-prism] Installing dependencies...
    call ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 exit /b 1
    call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 exit /b 1
)

echo [xray-prism] Starting server...
call ".venv\Scripts\python.exe" server.py %*

