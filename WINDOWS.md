# Ejecución en Windows

Esta rama está diseñada exclusivamente para Windows. No incluye compatibilidad
con macOS, Linux ni WSL.

## Requisitos

- Windows 10 u 11 de 64 bits.
- Python 3 instalado desde [python.org](https://www.python.org/downloads/windows/).
- Un compilador de C:
  - [MSYS2/MinGW-w64](https://www.msys2.org/), instalado en su ruta normal
    `C:\msys64`; o
  - Visual Studio Build Tools, con la carga de trabajo **Desarrollo para el escritorio con C++**.

Durante la instalación de Python, activa la opción **Add Python to PATH**.

Si eliges MSYS2, abre la terminal **MSYS2 UCRT64** una vez y ejecuta:

```bash
pacman -S --needed mingw-w64-ucrt-x86_64-gcc
```

## Instalación

1. Abre la carpeta del proyecto en el Explorador de archivos.
2. Ejecuta `setup_windows.bat`.
3. Cuando finalice, ejecuta `run_windows.bat`.

El script crea `.venv`, instala PySide6 y compila `src\main.c` como
`build\main.exe`.

## Desde PowerShell

También se puede ejecutar:

```powershell
.\setup_windows.bat
.\run_windows.bat
```

Si se modifica `src\main.c`, vuelve a ejecutar `setup_windows.bat` para
recompilarlo.
