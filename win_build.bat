@echo off
setlocal enabledelayedexpansion

set "ROOT_DIR=%~dp0"
set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "OUT_DIR=%ROOT_DIR%\build"
set "OUT_EXE=%OUT_DIR%\simulator.exe"

if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

if not defined CC (
	where clang >nul 2>nul
	if not errorlevel 1 set "CC=clang"
)
if not defined CC (
	where gcc >nul 2>nul
	if not errorlevel 1 set "CC=gcc"
)
if not defined CC (
	where cl >nul 2>nul
	if not errorlevel 1 set "CC=cl"
)
if not defined CC (
	echo No se encontro compilador C. Define CC=clang, CC=gcc o abre Developer Command Prompt para cl.
	exit /b 1
)

set "SOURCES="
for %%F in ("%ROOT_DIR%\src\simulator\*.c") do (
	set "SOURCES=!SOURCES! "%%~fF""
)

for %%C in ("%CC%") do set "CC_NAME=%%~nC"

if /i "%CC_NAME%"=="cl" (
	"%CC%" /nologo /W4 /Fe:"%OUT_EXE%" !SOURCES!
) else (
	"%CC%" -std=c99 -Wall -Wextra -pedantic !SOURCES! -o "%OUT_EXE%"
)

if errorlevel 1 exit /b 1
echo Compilado: %OUT_EXE%
