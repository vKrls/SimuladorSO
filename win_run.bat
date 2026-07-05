@echo off
setlocal enabledelayedexpansion

set "ROOT_DIR=%~dp0"
set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "VENV_DIR=%ROOT_DIR%\.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "REQUIREMENTS=%ROOT_DIR%\requirements.txt"
set "REQUIREMENTS_STAMP=%VENV_DIR%\.requirements.stamp"

if not defined SYSTEM_PYTHON (
	py -3 -c "import sys" >nul 2>nul
	if not errorlevel 1 set "SYSTEM_PYTHON=py -3"
)
if not defined SYSTEM_PYTHON (
	python -c "import sys" >nul 2>nul
	if not errorlevel 1 set "SYSTEM_PYTHON=python"
)
if not defined SYSTEM_PYTHON (
	echo No se encontro Python 3. Instala Python o agrega py/python al PATH.
	exit /b 1
)

if not exist "%VENV_PYTHON%" (
	echo Creando venv en %VENV_DIR%
	%SYSTEM_PYTHON% -m venv "%VENV_DIR%"
	if errorlevel 1 exit /b 1
)

if not exist "%VENV_PYTHON%" (
	echo No se pudo crear el entorno virtual en %VENV_DIR%
	exit /b 1
)

if exist "%REQUIREMENTS%" (
	set "NEEDS_INSTALL=0"
	if not exist "%REQUIREMENTS_STAMP%" (
		set "NEEDS_INSTALL=1"
	) else (
		fc "%REQUIREMENTS%" "%REQUIREMENTS_STAMP%" >nul 2>nul
		if errorlevel 1 set "NEEDS_INSTALL=1"
	)
	"%VENV_PYTHON%" -c "import PySide6" >nul 2>nul
	if errorlevel 1 set "NEEDS_INSTALL=1"

	if "!NEEDS_INSTALL!"=="1" (
		echo Instalando dependencias en %VENV_DIR%
		"%VENV_PYTHON%" -m pip install --upgrade pip
		if errorlevel 1 exit /b 1
		"%VENV_PYTHON%" -m pip install -r "%REQUIREMENTS%"
		if errorlevel 1 exit /b 1
		copy /y "%REQUIREMENTS%" "%REQUIREMENTS_STAMP%" >nul
	)
)

set "PYTHONPATH=%ROOT_DIR%\src;%PYTHONPATH%"
"%VENV_PYTHON%" -m gui.main
