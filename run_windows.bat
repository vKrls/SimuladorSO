@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo No existe el entorno virtual. Ejecutando la instalacion...
    call setup_windows.bat
    if errorlevel 1 exit /b 1
)

if not exist "build\main.exe" (
    echo No existe build\main.exe. Ejecutando la instalacion...
    call setup_windows.bat
    if errorlevel 1 exit /b 1
)

".venv\Scripts\python.exe" src\main.py
if errorlevel 1 (
    echo.
    echo El programa termino con un error.
    pause
    exit /b 1
)
