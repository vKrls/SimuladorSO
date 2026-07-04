#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VENV_DIR="$ROOT_DIR/.venv"
SYSTEM_PYTHON=${SYSTEM_PYTHON:-python3}
PYTHON=${PYTHON:-"$VENV_DIR/bin/python"}

if [ ! -x "$PYTHON" ]; then
	printf 'Creando venv en %s\n' "$VENV_DIR"
	"$SYSTEM_PYTHON" -m venv "$VENV_DIR"
fi

PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
	"$PYTHON" -m gui.main
