# Manual de Instalación - SimuladorSO

## macOS/Linux
1. `cd SimuladorSO`
2. `chmod +x build.sh run.sh`
3. `./build.sh`
4. `./run.sh`

`run.sh` crea `.venv`, instala `requirements.txt` y ejecuta la GUI. No se necesita activar un venv externo.

## Windows
1. `cd SimuladorSO`
2. `win_build.bat`
3. `win_run.bat`

## Comparaciones
`.venv/bin/python tools/compare_policies.py --build --context base --output-dir docs/final/comparisons`

## Verificación
- Confirmar que existe `build/simulator` o `build\simulator.exe`.
- Ejecutar la GUI, cargar `TEST` y presionar `RUN`.
- Revisar Gantt, memoria, PCB, procesos del SO y estadísticas.
- Generar `docs/final/comparisons/comparison_report.html`.
