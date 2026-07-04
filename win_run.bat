@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "VENV_DIR=%ROOT_DIR%\.venv"

if not defined PYTHON set "PYTHON=%VENV_DIR%\Scripts\python.exe"

if not exist "%PYTHON%" (
	echo Creando venv en %VENV_DIR%
	if defined SYSTEM_PYTHON (
		"%SYSTEM_PYTHON%" -m venv "%VENV_DIR%"
	) else (
		py -3 -m venv "%VENV_DIR%" 2>nul
		if errorlevel 1 python -m venv "%VENV_DIR%"
	)
)

set "PYTHONPATH=%ROOT_DIR%\src;%PYTHONPATH%"
"%PYTHON%" -m gui.main
