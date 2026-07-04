@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "VENV_DIR=%ROOT_DIR%\.venv"
set "REQUIREMENTS=%ROOT_DIR%\requirements.txt"
set "REQUIREMENTS_STAMP=%VENV_DIR%\.requirements.stamp"

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

if exist "%REQUIREMENTS%" (
	set "NEEDS_INSTALL=0"
	if not exist "%REQUIREMENTS_STAMP%" set "NEEDS_INSTALL=1"
	"%PYTHON%" -c "import PySide6" >nul 2>nul
	if errorlevel 1 set "NEEDS_INSTALL=1"

	if "%NEEDS_INSTALL%"=="1" (
		echo Instalando dependencias en %VENV_DIR%
		"%PYTHON%" -m pip install --upgrade pip
		if errorlevel 1 exit /b 1
		"%PYTHON%" -m pip install -r "%REQUIREMENTS%"
		if errorlevel 1 exit /b 1
		type nul > "%REQUIREMENTS_STAMP%"
	)
)

set "PYTHONPATH=%ROOT_DIR%\src;%PYTHONPATH%"
"%PYTHON%" -m gui.main
