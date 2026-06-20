@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo [1/4] Comprobando Python...
set "PY_LAUNCHER="
where py >nul 2>nul
if not errorlevel 1 set "PY_LAUNCHER=py -3"

if not defined PY_LAUNCHER (
    where python >nul 2>nul
    if not errorlevel 1 set "PY_LAUNCHER=python"
)

if not defined PY_LAUNCHER (
    echo ERROR: No se encontro Python.
    echo Instala Python 3 desde https://www.python.org/downloads/windows/
    echo y activa la opcion "Add Python to PATH".
    exit /b 1
)

echo [2/4] Creando el entorno virtual...
if not exist ".venv\Scripts\python.exe" (
    %PY_LAUNCHER% -m venv .venv
    if errorlevel 1 exit /b 1
)

echo [3/4] Instalando dependencias de Python...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo [4/4] Compilando el simulador en C...
if not exist build mkdir build

set "GCC_COMMAND="
where gcc >nul 2>nul
if not errorlevel 1 set "GCC_COMMAND=gcc"
if not defined GCC_COMMAND if exist "C:\msys64\ucrt64\bin\gcc.exe" set "GCC_COMMAND=C:\msys64\ucrt64\bin\gcc.exe"
if not defined GCC_COMMAND if exist "C:\msys64\mingw64\bin\gcc.exe" set "GCC_COMMAND=C:\msys64\mingw64\bin\gcc.exe"

if defined GCC_COMMAND (
    "%GCC_COMMAND%" -std=c11 -O2 -Wall -Wextra src\main.c -o build\main.exe
    if errorlevel 1 exit /b 1
    goto success
)

set "VS_INSTALL="
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if exist "%VSWHERE%" (
    for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VS_INSTALL=%%i"
    if defined VS_INSTALL call "!VS_INSTALL!\VC\Auxiliary\Build\vcvars64.bat" >nul
)

where cl >nul 2>nul
if not errorlevel 1 (
    cl /nologo /O2 /W3 /utf-8 /D_CRT_SECURE_NO_WARNINGS src\main.c /Fe:build\main.exe
    if errorlevel 1 exit /b 1
    if exist main.obj del main.obj
    goto success
)

where clang >nul 2>nul
if not errorlevel 1 (
    clang -std=c11 -O2 -Wall -Wextra src\main.c -o build\main.exe
    if errorlevel 1 exit /b 1
    goto success
)

echo ERROR: No se encontro un compilador de C.
echo Instala una de estas opciones y vuelve a ejecutar este archivo:
echo   - MSYS2/MinGW-w64: https://www.msys2.org/
echo   - Visual Studio Build Tools con "Desarrollo para el escritorio con C++"
exit /b 1

:success
echo.
echo Instalacion completada.
echo Ejecuta run_windows.bat para abrir el simulador.
exit /b 0
