@echo off
chcp 65001 > nul
title Dependency Installer and Updater - TikTok Extractor

echo ==========================================================
echo   UPDATING PYTHON ENVIRONMENT AND PROJECT DEPENDENCIES
echo ==========================================================
echo.

:: 1. Upgrade PIP
echo [1/3] Upgrading pip package manager...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to execute Python. Ensure Python is installed and added to your Windows PATH.
    echo.
    pause
    exit /b %errorlevel%
)
echo.

:: 2. Install or update dependencies from requirements.txt
echo [2/3] Installing / Updating libraries (yt-dlp, curl_cffi, playwright)...
python -m pip install -U -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] An error occurred while installing the required packages.
    echo.
    pause
    exit /b %errorlevel%
)
echo.

:: 3. Download/Update Playwright browser binaries
echo [3/3] Installing Chromium browser for Playwright...
playwright install chromium
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to install Chromium for Playwright.
    echo.
    pause
    exit /b %errorlevel%
)
echo.

echo ==========================================================
echo   ALL DEPENDENCIES INSTALLED AND UPDATED SUCCESSFULLY!
echo ==========================================================
echo.
echo You can now run your script with: python user.py
echo.
pause