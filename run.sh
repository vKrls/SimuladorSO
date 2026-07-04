#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VENV_DIR="/Users/vkrls/.venvs/SimuladorSO"
PYTHON=${PYTHON:-"$VENV_DIR/bin/python"}

if [ ! -x "$PYTHON" ]; then
	printf 'No se encontró el Python del venv: %s\n' "$PYTHON" >&2
	exit 1
fi

PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
	"$PYTHON" -m gui.main
