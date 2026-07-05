# Verificacion local de entrega

Fecha: 05/07/2026

Comandos ejecutados:

```sh
./build.sh
/Users/vkrls/.venvs/SimuladorSO/bin/python -m compileall -q src/gui
/Users/vkrls/.venvs/SimuladorSO/bin/python docs/final/generate_final_docs.py
printf 'SET_SEED 1234\nSET_CONFIG 0 0 0 0.1 100\nTEST\nRUN\nSTOP\n' | ./build/simulator
```

Resultados:

- `./build.sh` compilo correctamente y genero `build/simulator`.
- Los modulos Python de `src/gui` compilaron sin errores de sintaxis.
- Los documentos Word se abrieron correctamente con `python-docx`.
- El simulador C emitio `SIM_DATA`, recibio la configuracion FCFS + First Fit y cargo procesos `TEST`.
- La comparacion base esta generada en `docs/final/comparisons/comparison_report.html`.

Nota de entrega:

- `.gitignore` permite versionar `docs/final` y mantiene ignorada la documentacion local fuera de esa carpeta.
