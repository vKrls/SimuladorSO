#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CC=${CC:-cc}

mkdir -p "$ROOT_DIR/build"

"$CC" -std=c99 -Wall -Wextra -pedantic \
	"$ROOT_DIR"/src/simulator/*.c \
	-o "$ROOT_DIR/build/simulator"

printf 'Compilado: %s\n' "$ROOT_DIR/build/simulator"
