@echo off
title Custom Tests Battery - Development Mode
echo 🪟 Windows Development Mode
echo Starting development launcher...
echo.
python dev_tools/dev_launcher.py
if errorlevel 1 (
    echo.
    echo ❌ Error: Make sure Python is installed and in your PATH
    echo ❌ Also ensure you've installed requirements: pip install -r requirements-dev.txt
    pause
)