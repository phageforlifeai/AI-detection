@echo off
setlocal
cd /d "%~dp0"

set REPO_URL=https://github.com/phageforlifeai/AI-detection.git

echo ============================================================
echo   Uploading SciGram to %REPO_URL%
echo ============================================================

where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Git is not installed on this PC.
    echo Either install Git from https://git-scm.com/download/win
    echo OR drag-and-drop all files in this folder directly onto:
    echo   https://github.com/phageforlifeai/AI-detection/upload/main
    pause
    exit /b 1
)

if not exist ".git" (
    git init -b main
)

git add -A
git diff --cached --quiet
if %ERRORLEVEL% NEQ 0 (
    git commit -m "Initial commit: SciGram AI detector & scientific structure analyzer"
)

git remote remove origin >nul 2>nul
git remote add origin "%REPO_URL%"
git branch -M main

echo.
echo Pushing to GitHub ^(a browser sign-in window may open if needed^)...
git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Uploaded to https://github.com/phageforlifeai/AI-detection
) else (
    echo.
    echo [ERROR] Push failed. Make sure you are signed in as phageforlifeai.
)
pause
