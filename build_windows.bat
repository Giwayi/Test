@echo off
title EnergieBerater KI - Setup
chcp 1252 >nul 2>&1
cls

echo.
echo  ================================================
echo   EnergieBerater KI - Setup
echo  ================================================
echo.

:: Python suchen
set PYTHON=
for %%D in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
    "C:\Program Files\Python313\python.exe"
    "C:\Program Files\Python312\python.exe"
) do (
    if not defined PYTHON if exist %%D set PYTHON=%%D
)
if not defined PYTHON (
    where python >nul 2>&1
    if not errorlevel 1 (
        python -c "import sys;print(sys.executable)" >"%TEMP%\p.txt" 2>nul
        set /p PX=<"%TEMP%\p.txt"
        echo %PX% | findstr /i "WindowsApps" >nul
        if errorlevel 1 set PYTHON=python
    )
)
if not defined PYTHON (
    echo FEHLER: Python nicht gefunden!
    echo Bitte installieren: python.org/downloads
    echo Wichtig: "Add Python to PATH" anhaken!
    pause & exit /b 1
)

echo Python gefunden:
%PYTHON% --version
echo.

:: Alles weitere macht das Python-Skript
%PYTHON% build_setup.py
if errorlevel 1 (
    echo.
    echo Setup fehlgeschlagen - siehe Fehlermeldung oben.
    pause & exit /b 1
)
pause
