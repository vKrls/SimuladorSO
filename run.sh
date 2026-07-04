#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VENV_DIR="$ROOT_DIR/.venv"
REQUIREMENTS="$ROOT_DIR/requirements.txt"
REQUIREMENTS_STAMP="$VENV_DIR/.requirements.stamp"
if [ "${SYSTEM_PYTHON:-}" = "" ]; then
	if [ -x /opt/homebrew/bin/python3.12 ]; then
		SYSTEM_PYTHON=/opt/homebrew/bin/python3.12
	else
		SYSTEM_PYTHON=python3
	fi
fi
PYTHON=${PYTHON:-"$VENV_DIR/bin/python"}

create_venv()
{
	printf 'Creando venv en %s\n' "$VENV_DIR"
	rm -rf "$VENV_DIR"
	"$SYSTEM_PYTHON" -m venv "$VENV_DIR"
}

if [ -f "$VENV_DIR/pyvenv.cfg" ] &&
   grep -q "/Applications/Xcode.app" "$VENV_DIR/pyvenv.cfg"; then
	printf 'Recreando venv local con %s\n' "$SYSTEM_PYTHON"
	create_venv
fi

if [ ! -x "$PYTHON" ]; then
	create_venv
fi

if [ -f "$REQUIREMENTS" ]; then
	NEEDS_INSTALL=0
	if [ ! -f "$REQUIREMENTS_STAMP" ] ||
	   [ "$REQUIREMENTS" -nt "$REQUIREMENTS_STAMP" ] ||
	   ! "$PYTHON" -c "import PySide6" >/dev/null 2>&1; then
		NEEDS_INSTALL=1
	fi

	if [ "$NEEDS_INSTALL" -eq 1 ]; then
		printf 'Instalando dependencias en %s\n' "$VENV_DIR"
		"$PYTHON" -m pip install --upgrade pip
		"$PYTHON" -m pip install -r "$REQUIREMENTS"
		touch "$REQUIREMENTS_STAMP"
	fi
fi

if ! "$PYTHON" - <<'PY' >/dev/null 2>&1
import subprocess
import sys

code = "from PySide6.QtWidgets import QApplication; app = QApplication([])"
result = subprocess.run(
    [sys.executable, "-c", code],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
raise SystemExit(0 if result.returncode == 0 else 1)
PY
then
	printf 'El venv local no puede cargar Qt; recreando dependencias.\n'
	create_venv
	"$PYTHON" -m pip install --upgrade pip
	"$PYTHON" -m pip install -r "$REQUIREMENTS"
	touch "$REQUIREMENTS_STAMP"
fi

PYSIDE6_DIR=$("$PYTHON" -c "from pathlib import Path; import PySide6; print(Path(PySide6.__file__).resolve().parent)")
QT_PLUGIN_PATH="$PYSIDE6_DIR/Qt/plugins"
QT_QPA_PLATFORM_PLUGIN_PATH="$QT_PLUGIN_PATH/platforms"
QT_QPA_PLATFORM=cocoa
DYLD_FRAMEWORK_PATH="$PYSIDE6_DIR/Qt/lib${DYLD_FRAMEWORK_PATH:+:$DYLD_FRAMEWORK_PATH}"
DYLD_LIBRARY_PATH="$PYSIDE6_DIR/Qt/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
export QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH QT_QPA_PLATFORM
export DYLD_FRAMEWORK_PATH DYLD_LIBRARY_PATH

PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
	"$PYTHON" -m gui.main
