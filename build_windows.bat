@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Build PyQt6 Windows executable

REM ========== SETTINGS ==========
set "APPNAME=MyPyQt6App"
set "ENTRY=welcome.py"   REM <-- change to your real entrypoint if different

REM ========== CLEAN OLD BUILD OUTPUTS ==========
if exist build rmdir /S /Q build
if exist dist rmdir /S /Q dist
if exist __pycache__ rmdir /S /Q __pycache__

REM ========== PYTHON & DEPENDENCIES ==========
python -m pip install --upgrade pip

REM Install your app deps if a requirements file exists
if exist requirements.txt (
    echo Installing requirements.txt...
    python -m pip install -r requirements.txt
) else (
    echo No requirements.txt found; installing minimal deps...
    python -m pip install PyQt6
)

REM Packager
python -m pip install pyinstaller

REM ========== GATHER ASSETS TO INCLUDE ==========
REM Add common file types next to the EXE so relative paths keep working
set "ADDDATA="
for %%F in (*.csv *.txt *.ui *.json *.png *.ico *.wav) do (
    set "ADDDATA=!ADDDATA! --add-data ""%%F;."""
)

REM Ensure specific datasets are included (safe even if missing)
if exist sentence_dictionary.csv set "ADDDATA=!ADDDATA! --add-data ""sentence_dictionary.csv;."""
if exist stimulus_data.txt      set "ADDDATA=!ADDDATA! --add-data ""stimulus_data.txt;."""
if exist vmtcvc.txt             set "ADDDATA=!ADDDATA! --add-data ""vmtcvc.txt;."""

REM Common asset folders (copy entire folder into dist)
for %%D in (assets resources icons data) do (
    if exist "%%D" (
        set "ADDDATA=!ADDDATA! --add-data ""%%D;%%D"""
    )
)

REM ========== BUILD ==========
pyinstaller ^
  --name "%APPNAME%" ^
  --windowed ^
  --noconfirm ^
  --clean ^
  --collect-all PyQt6 ^
  !ADDDATA! ^
  "%ENTRY%"

echo.
if exist "dist\%APPNAME%\%APPNAME%.exe" (
  echo ✅ Build finished: dist\%APPNAME%\%APPNAME%.exe
) else (
  echo ⚠️  Build completed, check dist\%APPNAME% for output and any missing assets.
)
endlocal
