@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo   SciGram - AI Detection ^& Scientific Structure Analyzer
echo ============================================================

REM Detect Python launcher (py -3 or python)
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set PY_CMD=python
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        set PY_CMD=py -3
    ) else (
        echo [ERROR] Python 3.10+ was not found on your PC.
        echo Please install Python from https://www.python.org/downloads/
        echo ^(Make sure to check "Add python.exe to PATH" during installation^).
        pause
        exit /b 1
    )
)

REM Create virtual environment on first run
if not exist ".venv\Scripts\python.exe" (
    echo [1/2] Creating isolated virtual environment ^(.venv^)...
    %PY_CMD% -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Could not create virtual environment.
        pause
        exit /b 1
    )
    echo [2/2] Installing SciGram dependencies ^(first-time setup^)...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -e .
)

echo.
echo Starting SciGram Web Dashboard at http://127.0.0.1:8000 ...
echo ^(First launch will download ~158 MB of quantized neural models once^)
echo Keep this window open while using SciGram. Press Ctrl+C to stop.
echo.

start "" cmd /c "timeout /t 4 /nobreak >nul & start http://127.0.0.1:8000"
".venv\Scripts\python.exe" server.py
pause
