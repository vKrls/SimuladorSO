#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VENV_DIR="$ROOT_DIR/.venv"
REQUIREMENTS="$ROOT_DIR/requirements.txt"
REQUIREMENTS_STAMP="$VENV_DIR/.requirements.stamp"
SYSTEM_PYTHON=${SYSTEM_PYTHON:-python3}
PYTHON=${PYTHON:-"$VENV_DIR/bin/python"}

if [ ! -x "$PYTHON" ]; then
	printf 'Creando venv en %s\n' "$VENV_DIR"
	"$SYSTEM_PYTHON" -m venv "$VENV_DIR"
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

PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
	"$PYTHON" -m gui.main
