#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VENV_DIR="${VENV_DIR:-"$ROOT_DIR/.venv"}"
REQUIREMENTS="$ROOT_DIR/requirements.txt"
REQUIREMENTS_STAMP="$VENV_DIR/.requirements.stamp"
PYTHON=${PYTHON:-"$VENV_DIR/bin/python"}
OS_NAME=$(uname -s)

find_python()
{
	if [ -n "${SYSTEM_PYTHON:-}" ]; then
		printf '%s\n' "$SYSTEM_PYTHON"
		return 0
	fi

	if [ "$OS_NAME" = "Darwin" ]; then
		for candidate in \
			/opt/homebrew/bin/python3.12 \
			/usr/local/bin/python3.12 \
			python3.12 \
			python3
		do
			if [ -x "$candidate" ] || command -v "$candidate" >/dev/null 2>&1; then
				printf '%s\n' "$candidate"
				return 0
			fi
		done
	else
		for candidate in python3.12 python3; do
			if command -v "$candidate" >/dev/null 2>&1; then
				printf '%s\n' "$candidate"
				return 0
			fi
		done
	fi

	return 1
}

SYSTEM_PYTHON=$(find_python) || {
	printf 'No encontre Python 3. Instala python3 y vuelve a ejecutar ./run.sh\n' >&2
	exit 1
}

create_venv()
{
	printf 'Creando venv en %s con %s\n' "$VENV_DIR" "$SYSTEM_PYTHON"
	rm -rf "$VENV_DIR"
	if ! "$SYSTEM_PYTHON" -m venv "$VENV_DIR"; then
		printf '\nNo se pudo crear el entorno virtual.\n' >&2
		printf 'Debian/Ubuntu: sudo apt install python3-venv python3-pip\n' >&2
		printf 'Arch: sudo pacman -S python python-pip\n' >&2
		exit 1
	fi
}

install_requirements()
{
	if [ ! -f "$REQUIREMENTS" ]; then
		return 0
	fi

	printf 'Instalando dependencias en %s\n' "$VENV_DIR"
	"$PYTHON" -m pip install --upgrade pip
	"$PYTHON" -m pip install -r "$REQUIREMENTS"
	touch "$REQUIREMENTS_STAMP"
}

ensure_dependencies()
{
	if [ ! -f "$REQUIREMENTS" ]; then
		return 0
	fi

	NEEDS_INSTALL=0
	if [ ! -f "$REQUIREMENTS_STAMP" ] ||
	   [ "$REQUIREMENTS" -nt "$REQUIREMENTS_STAMP" ] ||
	   ! "$PYTHON" -c "import PySide6" >/dev/null 2>&1; then
		NEEDS_INSTALL=1
	fi

	if [ "$NEEDS_INSTALL" -eq 1 ]; then
		install_requirements
	fi
}

setup_qt_environment()
{
	PYSIDE6_DIR=$("$PYTHON" - <<'PY'
from pathlib import Path
import PySide6

print(Path(PySide6.__file__).resolve().parent)
PY
)

	QT_PLUGIN_ROOT="$PYSIDE6_DIR/Qt/plugins"
	QT_PLATFORM_DIR="$QT_PLUGIN_ROOT/platforms"
	QT_LIB_DIR="$PYSIDE6_DIR/Qt/lib"

	QT_PLUGIN_PATH="$QT_PLUGIN_ROOT"
	QT_QPA_PLATFORM_PLUGIN_PATH="$QT_PLATFORM_DIR"
	export QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH

	case "$OS_NAME" in
		Darwin)
			QT_QPA_PLATFORM=${QT_QPA_PLATFORM:-cocoa}
			DYLD_FRAMEWORK_PATH="$QT_LIB_DIR${DYLD_FRAMEWORK_PATH:+:$DYLD_FRAMEWORK_PATH}"
			DYLD_LIBRARY_PATH="$QT_LIB_DIR${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
			export QT_QPA_PLATFORM DYLD_FRAMEWORK_PATH DYLD_LIBRARY_PATH
			;;
		Linux)
			LD_LIBRARY_PATH="$QT_LIB_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
			export LD_LIBRARY_PATH

			if [ -z "${QT_QPA_PLATFORM:-}" ]; then
				if [ -n "${DISPLAY:-}" ] && [ -f "$QT_PLATFORM_DIR/libqxcb.so" ]; then
					QT_QPA_PLATFORM=xcb
				elif [ -n "${WAYLAND_DISPLAY:-}" ] &&
				     { [ -f "$QT_PLATFORM_DIR/libqwayland-generic.so" ] ||
				       [ -f "$QT_PLATFORM_DIR/libqwayland-egl.so" ]; }; then
					QT_QPA_PLATFORM=wayland
				else
					printf 'No detecte DISPLAY ni WAYLAND_DISPLAY para abrir la GUI.\n' >&2
					printf 'Si estas por SSH, usa X forwarding; si solo quieres probar imports, ejecuta QT_QPA_PLATFORM=offscreen ./run.sh\n' >&2
					exit 1
				fi
			fi
			export QT_QPA_PLATFORM
			;;
		*)
			if [ -z "${QT_QPA_PLATFORM:-}" ]; then
				QT_QPA_PLATFORM=xcb
			fi
			export QT_QPA_PLATFORM
			;;
	esac
}

check_qt()
{
	"$PYTHON" - <<'PY' >/dev/null 2>&1
from PySide6.QtWidgets import QApplication

app = QApplication([])
app.quit()
PY
}

print_linux_qt_help()
{
	if [ "$OS_NAME" != "Linux" ]; then
		return 0
	fi

	cat >&2 <<'EOF'

Qt no pudo inicializar el plugin grafico.
En Linux esto casi siempre significa que faltan librerias del sistema para xcb/wayland.

Debian/Ubuntu:
  sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libxcb-xinerama0 libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-keysyms1 libegl1

Arch:
  sudo pacman -S xcb-util-cursor xcb-util-keysyms xcb-util-renderutil xcb-util-wm libxkbcommon-x11 libxcb qt6-wayland

Tambien puedes forzar backend:
  QT_QPA_PLATFORM=xcb ./run.sh
  QT_QPA_PLATFORM=wayland ./run.sh
EOF
}

if [ -f "$VENV_DIR/pyvenv.cfg" ] &&
   grep -q "/Applications/Xcode.app" "$VENV_DIR/pyvenv.cfg"; then
	printf 'Recreando venv local con %s\n' "$SYSTEM_PYTHON"
	create_venv
fi

if [ ! -x "$PYTHON" ]; then
	create_venv
fi

ensure_dependencies
setup_qt_environment

if ! check_qt; then
	printf 'El venv local no pudo cargar Qt; recreando dependencias una vez.\n' >&2
	create_venv
	install_requirements
	setup_qt_environment

	if ! check_qt; then
		print_linux_qt_help
		printf '\nNo se pudo iniciar Qt con QT_QPA_PLATFORM=%s\n' "$QT_QPA_PLATFORM" >&2
		exit 1
	fi
fi

PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
	"$PYTHON" -m gui.main
