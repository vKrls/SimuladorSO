#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT_DIR / "docs" / "comparisons"
SIM_DATA_PREFIX = "SIM_DATA "
LEGACY_OUTPUT_FILES = (
    "comparison_report.md",
    "comparison_results.csv",
    "comparison_processes.csv",
    "comparison_results.json",
)


SCHEDULERS = [
    (0, "FCFS"),
    (1, "SJF no expropiativo"),
    (2, "SJF expropiativo"),
    (3, "Round Robin"),
    (4, "Prioridad no expropiativa"),
    (5, "Prioridad expropiativa"),
]

MEMORY_STRATEGIES = [
    (0, "First Fit"),
    (1, "Best Fit"),
    (2, "Worst Fit"),
]


@dataclass(frozen=True)
class Context:
    key: str
    name: str
    switch_cost: float
    quantum: float
    speed: int
    description: str


CONTEXTS = [
    Context(
        key="base",
        name="Contexto base",
        switch_cost=0.1,
        quantum=5.0,
        speed=100,
        description="Cambio de contexto bajo, util para observar el planificador.",
    ),
    Context(
        key="costoso",
        name="Contexto con cambio costoso",
        switch_cost=1.0,
        quantum=5.0,
        speed=100,
        description="Cambio de contexto mas caro, util para ver el costo de desalojar.",
    ),
]


def parse_args() -> argparse.Namespace:
    executable = default_executable()
    parser = argparse.ArgumentParser(
        description="Ejecuta TEST con todas las politicas y genera un informe comparativo."
    )
    parser.add_argument("--executable", default=str(executable), help="Binario del simulador C.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Carpeta de salida.")
    parser.add_argument("--seed", type=int, default=1234, help="Semilla base para SET_SEED.")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout por corrida en segundos.")
    parser.add_argument(
        "--context",
        choices=["all", *[context.key for context in CONTEXTS]],
        default="all",
        help="Contexto a ejecutar.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Limita corridas para pruebas.")
    parser.add_argument("--build", action="store_true", help="Compila antes de ejecutar.")
    return parser.parse_args()


def default_executable() -> Path:
    if os.name == "nt":
        return ROOT_DIR / "build" / "simulator.exe"
    return ROOT_DIR / "build" / "simulator"


def maybe_build() -> None:
    if os.name == "nt":
        command = [str(ROOT_DIR / "win_build.bat")]
    else:
        command = [str(ROOT_DIR / "build.sh")]
    subprocess.run(command, cwd=ROOT_DIR, check=True)


def selected_contexts(key: str) -> list[Context]:
    if key == "all":
        return CONTEXTS
    return [context for context in CONTEXTS if context.key == key]


def run_simulation(
    executable: Path,
    context: Context,
    scheduler_id: int,
    scheduler_name: str,
    memory_id: int,
    memory_name: str,
    seed: int,
    timeout: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    commands = [
        f"SET_CONFIG {scheduler_id} {memory_id} {context.quantum:.3f} "
        f"{context.switch_cost:.3f} {context.speed}",
        f"SET_SEED {seed}",
        "TEST",
        "RUN",
    ]
    process = subprocess.Popen(
        [str(executable)],
        cwd=ROOT_DIR,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = process.communicate("\n".join(commands) + "\n", timeout=timeout)
    if process.returncode != 0:
        raise RuntimeError(
            f"Fallo {scheduler_name} / {memory_name} / {context.name}: {stderr.strip()}"
        )

    states = []
    logs = []
    for line in stdout.splitlines():
        if line.startswith(SIM_DATA_PREFIX):
            try:
                states.append(json.loads(line[len(SIM_DATA_PREFIX):]))
            except json.JSONDecodeError:
                logs.append(f"JSON invalido: {line[:160]}")
        elif line.startswith("LOG "):
            logs.append(line)

    if not states:
        raise RuntimeError(f"El simulador no envio SIM_DATA para {scheduler_name}/{memory_name}.")

    row = summarize_simulation(
        states,
        context=context,
        scheduler=scheduler_name,
        memory=memory_name,
        seed=seed,
    )
    process_rows = summarize_processes(
        states[-1],
        context=context.name,
        scheduler=scheduler_name,
        memory=memory_name,
        seed=seed,
    )
    return row, process_rows, logs


def summarize_simulation(
    states: list[dict[str, Any]],
    *,
    context: Context,
    scheduler: str,
    memory: str,
    seed: int,
) -> dict[str, Any]:
    final = states[-1]
    stats = final.get("stats", {})
    user_processes = [process for process in final.get("processes", []) if not process.get("is_system")]
    memory_metrics = summarize_memory(states)

    row: dict[str, Any] = {
        "context": context.name,
        "scheduler": scheduler,
        "memory": memory,
        "seed": seed,
        "avg_ready_time": number(stats.get("avg_ready_time")),
        "avg_turnaround": number(stats.get("avg_turnaround")),
        "avg_response": number(stats.get("avg_response")),
        "throughput": number(stats.get("throughput")),
        "cpu_util": number(stats.get("cpu_util")),
        "total_time": number(stats.get("total_time")),
        "completed": int(number(stats.get("completed"))),
        "errors": int(number(stats.get("errors"))),
        "interrupts": int(number(stats.get("interrupts"))),
        "swap_outs": int(number(stats.get("swap_outs"))),
        "swap_ins": int(number(stats.get("swap_ins"))),
        "context_switches": int(number(stats.get("context_switches"))),
        "context_switch_time": number(stats.get("context_switch_time")),
        "avg_cpu_time": average_scheduler_field(user_processes, "cpu_time"),
        "avg_blocked_time": average_scheduler_field(user_processes, "blocked_time"),
        "avg_nonresident_time": average_scheduler_field(user_processes, "nonresident_time"),
    }
    row.update(memory_metrics)
    return row


def summarize_memory(states: list[dict[str, Any]]) -> dict[str, float]:
    runtime_states = [
        state for state in states
        if number(state.get("current_time")) > 0.0
        and int(number(state.get("stats", {}).get("completed"))) < 20
    ]
    if not runtime_states:
        runtime_states = states

    external_fragments = []
    internal_waste = []
    free_block_counts = []
    free_memory = []
    used_memory = []

    for state in runtime_states:
        memory = state.get("memory", {})
        block_size = int(number(memory.get("block_size_kb"), 4))
        total_kb = number(memory.get("total_kb"))
        free_kb = number(memory.get("free_kb"))
        blocks = list(memory.get("blocks", []))
        free_blocks = [block for block in blocks if block.get("owner_pid") is None]
        largest_free_kb = max(
            (number(block.get("length_blocks")) * block_size for block in free_blocks),
            default=0.0,
        )
        external = 0.0 if free_kb <= 0 else (free_kb - largest_free_kb) / free_kb * 100.0
        external_fragments.append(external)
        free_block_counts.append(float(len(free_blocks)))
        free_memory.append(free_kb)
        used_memory.append(max(0.0, total_kb - free_kb))

        resident_waste = 0.0
        for process in state.get("processes", []):
            if process.get("is_system") or not process.get("resident"):
                continue
            resident_waste += number(process.get("memory", {}).get("waste_kb"))
        internal_waste.append(resident_waste)

    return {
        "avg_external_fragmentation_pct": mean_or_zero(external_fragments),
        "max_external_fragmentation_pct": max(external_fragments, default=0.0),
        "avg_internal_waste_mb": mean_or_zero(internal_waste) / 1024.0,
        "max_internal_waste_mb": max(internal_waste, default=0.0) / 1024.0,
        "avg_free_block_count": mean_or_zero(free_block_counts),
        "max_free_block_count": max(free_block_counts, default=0.0),
        "min_free_memory_mb": min(free_memory, default=0.0) / 1024.0,
        "peak_used_memory_mb": max(used_memory, default=0.0) / 1024.0,
    }


def summarize_processes(
    final_state: dict[str, Any],
    *,
    context: str,
    scheduler: str,
    memory: str,
    seed: int,
) -> list[dict[str, Any]]:
    rows = []
    for process in final_state.get("processes", []):
        if process.get("is_system"):
            continue
        scheduler_data = process.get("scheduler", {})
        rows.append(
            {
                "context": context,
                "scheduler": scheduler,
                "memory": memory,
                "seed": seed,
                "pid": process.get("pid"),
                "name": process.get("name"),
                "state": process.get("state"),
                "arrival_time": number(scheduler_data.get("arrival_time")),
                "burst_time": number(scheduler_data.get("burst_time")),
                "cpu_time": number(scheduler_data.get("cpu_time")),
                "ready_time": number(scheduler_data.get("ready_time")),
                "response_time": number(scheduler_data.get("response_time")),
                "turnaround_time": number(scheduler_data.get("turnaround_time")),
                "blocked_time": number(scheduler_data.get("blocked_time")),
                "nonresident_time": number(scheduler_data.get("nonresident_time")),
                "context_switches": int(number(scheduler_data.get("context_switches"))),
                "interrupts": int(number(process.get("interrupts", {}).get("total"))),
                "swap_count": int(number(process.get("swap_count"))),
                "memory_mb": number(process.get("memory", {}).get("required_kb")) / 1024.0,
                "error_code": process.get("error", {}).get("code", ""),
            }
        )
    return rows


def add_scores(rows: list[dict[str, Any]]) -> None:
    for context in sorted({row["context"] for row in rows}):
        group = [row for row in rows if row["context"] == context]
        performance_metrics = [
            ("avg_turnaround", False),
            ("avg_ready_time", False),
            ("avg_response", False),
            ("total_time", False),
            ("throughput", True),
            ("cpu_util", True),
        ]
        memory_metrics = [
            ("avg_external_fragmentation_pct", False),
            ("max_external_fragmentation_pct", False),
            ("avg_internal_waste_mb", False),
            ("max_internal_waste_mb", False),
            ("swap_outs", False),
            ("avg_free_block_count", False),
        ]
        apply_rank_score(group, performance_metrics, "performance_score")
        apply_rank_score(group, memory_metrics, "memory_score")


def apply_rank_score(
    rows: list[dict[str, Any]],
    metrics: list[tuple[str, bool]],
    output_key: str,
) -> None:
    scores = {id(row): [] for row in rows}
    for metric, higher_is_better in metrics:
        ranked = sorted(rows, key=lambda row: number(row.get(metric)), reverse=higher_is_better)
        for index, row in enumerate(ranked, start=1):
            scores[id(row)].append(index)
    for row in rows:
        row[output_key] = mean(scores[id(row)])


def average_scheduler_field(processes: list[dict[str, Any]], field: str) -> float:
    values = [number(process.get("scheduler", {}).get(field)) for process in processes]
    return mean_or_zero(values)


def number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def mean_or_zero(values: list[float]) -> float:
    return mean(values) if values else 0.0


def remove_legacy_outputs(output_dir: Path) -> None:
    for file_name in LEGACY_OUTPUT_FILES:
        path = output_dir / file_name
        if path.exists():
            path.unlink()


def generate_html_report(
    rows: list[dict[str, Any]],
    process_rows: list[dict[str, Any]],
    output_dir: Path,
    seed: int,
) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    contexts = sorted({row["context"] for row in rows})
    best_cards = []
    for context in contexts:
        group = [row for row in rows if row["context"] == context]
        best_performance = min(group, key=lambda row: row["performance_score"])
        best_memory = min(group, key=lambda row: row["memory_score"])
        best_cards.append(
            f"""
            <section class="summary-card">
                <p class="eyebrow">{escape(context)}</p>
                <h2>Ganadores</h2>
                <div class="winner-grid">
                    <div>
                        <span class="label">Rendimiento</span>
                        <strong>{escape(best_performance["scheduler"])} + {escape(best_performance["memory"])}</strong>
                        <small>TAT {best_performance["avg_turnaround"]:.2f} · Resp. {best_performance["avg_response"]:.2f}</small>
                    </div>
                    <div>
                        <span class="label">Memoria</span>
                        <strong>{escape(best_memory["scheduler"])} + {escape(best_memory["memory"])}</strong>
                        <small>Frag. {best_memory["avg_external_fragmentation_pct"]:.2f}% · Waste {best_memory["avg_internal_waste_mb"]:.2f} MB</small>
                    </div>
                </div>
            </section>
            """
        )

    context_blocks = []
    for context in contexts:
        group = [row for row in rows if row["context"] == context]
        context_blocks.append(
            f"""
            <section class="panel">
                <div class="section-title">
                    <div>
                        <p class="eyebrow">Matriz</p>
                        <h2>{escape(context)}</h2>
                    </div>
                    <p>La celda muestra TAT, fragmentacion externa y CPU. Verde suele ser mejor.</p>
                </div>
                {html_matrix(group)}
            </section>
            """
        )

    html_doc = f"""<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Informe comparativo de politicas</title>
    <style>
        :root {{
            --bg: #101418;
            --panel: #171d23;
            --panel-2: #1d252d;
            --line: #2b3844;
            --text: #f2f7fb;
            --muted: #a9b8c4;
            --good: #5fbf8f;
            --mid: #e2b85d;
            --bad: #e26d6d;
            --accent: #75b7e8;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            background: var(--bg);
            color: var(--text);
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            line-height: 1.45;
        }}
        main {{
            width: min(1280px, calc(100% - 40px));
            margin: 0 auto;
            padding: 34px 0 44px;
        }}
        header {{
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 28px;
            align-items: end;
            border-bottom: 1px solid var(--line);
            padding-bottom: 24px;
            margin-bottom: 24px;
        }}
        h1, h2, h3, p {{ margin-top: 0; }}
        h1 {{ font-size: clamp(30px, 4vw, 48px); line-height: 1.05; margin-bottom: 12px; }}
        h2 {{ font-size: 22px; margin-bottom: 14px; }}
        h3 {{ font-size: 15px; margin-bottom: 8px; color: var(--muted); font-weight: 600; }}
        .lead {{ color: var(--muted); max-width: 760px; margin-bottom: 0; }}
        .meta {{
            display: grid;
            gap: 8px;
            padding: 14px 16px;
            border: 1px solid var(--line);
            background: var(--panel);
            min-width: 240px;
        }}
        .meta span, .label, .eyebrow {{
            color: var(--muted);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: .06em;
        }}
        .card-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 16px;
            margin-bottom: 18px;
        }}
        .summary-card, .panel {{
            border: 1px solid var(--line);
            background: var(--panel);
            padding: 18px;
        }}
        .winner-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 12px;
        }}
        .winner-grid div {{
            border-left: 3px solid var(--accent);
            background: var(--panel-2);
            padding: 12px;
        }}
        strong {{ display: block; font-size: 16px; margin: 4px 0; }}
        small {{ color: var(--muted); }}
        .section-title {{
            display: flex;
            justify-content: space-between;
            gap: 18px;
            align-items: end;
            margin-bottom: 12px;
        }}
        .section-title p {{ color: var(--muted); margin-bottom: 0; max-width: 520px; }}
        .rank-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
            gap: 18px;
            margin: 18px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th, td {{
            border-bottom: 1px solid var(--line);
            padding: 9px 10px;
            text-align: left;
            vertical-align: top;
        }}
        th {{
            color: var(--muted);
            font-weight: 600;
            background: #131920;
        }}
        tr:last-child td {{ border-bottom: 0; }}
        .score-pill {{
            display: inline-flex;
            min-width: 52px;
            justify-content: center;
            padding: 3px 8px;
            color: #0f1519;
            background: var(--good);
            font-weight: 700;
        }}
        .matrix {{
            table-layout: fixed;
        }}
        .matrix td:not(:first-child) {{
            border: 1px solid var(--bg);
            color: #081015;
            font-weight: 700;
        }}
        .matrix small {{
            display: block;
            color: rgba(8, 16, 21, .74);
            font-weight: 600;
            margin-top: 2px;
        }}
        .legend {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            color: var(--muted);
            margin-top: 12px;
            font-size: 12px;
        }}
        .legend span {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .swatch {{
            width: 18px;
            height: 10px;
            display: inline-block;
        }}
        .files {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 10px;
        }}
        .file {{
            background: var(--panel-2);
            border: 1px solid var(--line);
            padding: 12px;
            color: var(--muted);
        }}
        code {{ color: var(--text); }}
        @media (max-width: 780px) {{
            header {{ grid-template-columns: 1fr; }}
            main {{ width: min(100% - 24px, 1280px); }}
            .rank-grid {{ grid-template-columns: 1fr; }}
            .section-title {{ display: block; }}
            table {{ font-size: 12px; }}
            th, td {{ padding: 8px; }}
        }}
    </style>
</head>
<body>
<main>
    <header>
        <div>
            <h1>Informe comparativo de politicas</h1>
            <p class="lead">Comparacion de 6 politicas de planificacion contra 3 estrategias de memoria, usando los 20 procesos definidos por <code>TEST</code>.</p>
        </div>
        <div class="meta">
            <div><span>Generado</span><br>{escape(generated)}</div>
            <div><span>Semilla</span><br>{seed}</div>
            <div><span>Combinaciones</span><br>{len(rows)}</div>
        </div>
    </header>

    <div class="card-grid">
        {''.join(best_cards)}
    </div>

    <section class="rank-grid">
        <div class="panel">
            <div class="section-title">
                <div>
                    <p class="eyebrow">Ranking</p>
                    <h2>Rendimiento</h2>
                </div>
            </div>
            {html_ranking(rows, "performance_score")}
        </div>
        <div class="panel">
            <div class="section-title">
                <div>
                    <p class="eyebrow">Ranking</p>
                    <h2>Memoria</h2>
                </div>
            </div>
            {html_ranking(rows, "memory_score")}
        </div>
    </section>

    {''.join(context_blocks)}

    <section class="panel">
        <div class="section-title">
            <div>
                <p class="eyebrow">Detalle</p>
                <h2>Todas las combinaciones</h2>
            </div>
            <p>Sirve para justificar la conclusion con numeros concretos.</p>
        </div>
        {html_combinations_table(rows)}
    </section>

    <section class="panel" style="margin-top:18px">
        <div class="section-title">
            <div>
                <p class="eyebrow">Procesos</p>
                <h2>Peores TAT observados</h2>
            </div>
            <p>Ayuda a encontrar politicas donde ciertos procesos se castigan demasiado.</p>
        </div>
        {html_process_table(process_rows)}
    </section>

    <section class="panel" style="margin-top:18px">
        <div class="section-title">
            <div>
                <p class="eyebrow">Metricas</p>
                <h2>Lectura rapida</h2>
            </div>
        </div>
        <table>
            <tbody>
                <tr><td><strong>Ready</strong></td><td>Tiempo promedio esperando CPU.</td></tr>
                <tr><td><strong>TAT</strong></td><td>Tiempo desde llegada hasta finalizacion.</td></tr>
                <tr><td><strong>Resp.</strong></td><td>Tiempo hasta la primera entrada a CPU.</td></tr>
                <tr><td><strong>CPU %</strong></td><td>Porcentaje del tiempo total en ejecucion.</td></tr>
                <tr><td><strong>Frag ext %</strong></td><td>Que tan partida queda la memoria libre.</td></tr>
                <tr><td><strong>Waste MB</strong></td><td>Desperdicio interno por redondeo a bloques.</td></tr>
            </tbody>
        </table>
    </section>

    <section class="panel" style="margin-top:18px">
        <div class="section-title">
            <div>
                <p class="eyebrow">Archivo</p>
                <h2>Salida generada</h2>
            </div>
        </div>
        <div class="files">
            <div class="file"><code>{escape(display_path(output_dir / "comparison_report.html"))}</code><br>Informe visual autocontenido.</div>
        </div>
    </section>
</main>
</body>
</html>
"""
    return html_doc


def html_ranking(rows: list[dict[str, Any]], score_key: str) -> str:
    sorted_rows = sorted(rows, key=lambda row: row[score_key])
    body = []
    for index, row in enumerate(sorted_rows, start=1):
        body.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td>{escape(row['context'])}</td>"
            f"<td>{escape(row['scheduler'])}</td>"
            f"<td>{escape(row['memory'])}</td>"
            f"<td><span class=\"score-pill\">{row[score_key]:.2f}</span></td>"
            f"<td>{row['avg_turnaround']:.2f}</td>"
            f"<td>{row['avg_external_fragmentation_pct']:.2f}%</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>#</th><th>Contexto</th><th>Planificacion</th>"
        "<th>Memoria</th><th>Score</th><th>TAT</th><th>Frag.</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
    )


def html_matrix(rows: list[dict[str, Any]]) -> str:
    by_pair = {(row["scheduler"], row["memory"]): row for row in rows}
    tat_values = [row["avg_turnaround"] for row in rows]
    frag_values = [row["avg_external_fragmentation_pct"] for row in rows]
    minimum = min([*tat_values, *frag_values], default=0.0)
    maximum = max([*tat_values, *frag_values], default=1.0)
    body = []
    for _, scheduler in SCHEDULERS:
        cells = [f"<td>{escape(scheduler)}</td>"]
        for _, memory in MEMORY_STRATEGIES:
            row = by_pair.get((scheduler, memory))
            if row is None:
                cells.append("<td>--</td>")
                continue
            intensity = normalized((row["avg_turnaround"] + row["avg_external_fragmentation_pct"]) / 2.0, minimum, maximum)
            color = heat_color(intensity)
            cells.append(
                f"<td style=\"background:{color}\">"
                f"TAT {row['avg_turnaround']:.2f}"
                f"<small>Frag {row['avg_external_fragmentation_pct']:.2f}% · CPU {row['cpu_util']:.1f}%</small>"
                "</td>"
            )
        body.append(f"<tr>{''.join(cells)}</tr>")
    return (
        "<table class=\"matrix\"><thead><tr><th>Planificacion</th><th>First Fit</th>"
        "<th>Best Fit</th><th>Worst Fit</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
        "<div class=\"legend\">"
        "<span><i class=\"swatch\" style=\"background:#5fbf8f\"></i>mejor</span>"
        "<span><i class=\"swatch\" style=\"background:#e2b85d\"></i>medio</span>"
        "<span><i class=\"swatch\" style=\"background:#e26d6d\"></i>peor</span>"
        "</div>"
    )


def html_combinations_table(rows: list[dict[str, Any]]) -> str:
    body = []
    for row in sorted(rows, key=lambda item: (item["context"], item["scheduler"], item["memory"])):
        body.append(
            "<tr>"
            f"<td>{escape(row['context'])}</td>"
            f"<td>{escape(row['scheduler'])}</td>"
            f"<td>{escape(row['memory'])}</td>"
            f"<td>{row['avg_ready_time']:.2f}</td>"
            f"<td>{row['avg_turnaround']:.2f}</td>"
            f"<td>{row['avg_response']:.2f}</td>"
            f"<td>{row['cpu_util']:.1f}</td>"
            f"<td>{row['throughput']:.4f}</td>"
            f"<td>{row['avg_external_fragmentation_pct']:.2f}%</td>"
            f"<td>{row['avg_internal_waste_mb']:.2f}</td>"
            f"<td>{int(row['swap_outs'])}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Contexto</th><th>Planificacion</th><th>Memoria</th>"
        "<th>Ready</th><th>TAT</th><th>Resp.</th><th>CPU %</th><th>Throughput</th>"
        "<th>Frag.</th><th>Waste MB</th><th>Swaps</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
    )


def html_process_table(process_rows: list[dict[str, Any]]) -> str:
    worst = sorted(process_rows, key=lambda row: number(row.get("turnaround_time")), reverse=True)[:15]
    body = []
    for row in worst:
        body.append(
            "<tr>"
            f"<td>{escape(row['context'])}</td>"
            f"<td>{escape(row['scheduler'])}</td>"
            f"<td>{escape(row['memory'])}</td>"
            f"<td>{escape(str(row['name']))}</td>"
            f"<td>{number(row.get('turnaround_time')):.2f}</td>"
            f"<td>{number(row.get('ready_time')):.2f}</td>"
            f"<td>{number(row.get('response_time')):.2f}</td>"
            f"<td>{number(row.get('blocked_time')):.2f}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Contexto</th><th>Planificacion</th><th>Memoria</th>"
        "<th>Proceso</th><th>TAT</th><th>Ready</th><th>Resp.</th><th>Blocked</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
    )


def normalized(value: float, minimum: float, maximum: float) -> float:
    if maximum <= minimum:
        return 0.0
    return max(0.0, min(1.0, (value - minimum) / (maximum - minimum)))


def heat_color(value: float) -> str:
    if value < 0.5:
        t = value / 0.5
        return blend("#5fbf8f", "#e2b85d", t)
    return blend("#e2b85d", "#e26d6d", (value - 0.5) / 0.5)


def blend(start: str, end: str, amount: float) -> str:
    amount = max(0.0, min(1.0, amount))
    start_rgb = hex_to_rgb(start)
    end_rgb = hex_to_rgb(end)
    mixed = [
        round(start_rgb[index] + (end_rgb[index] - start_rgb[index]) * amount)
        for index in range(3)
    ]
    return "#" + "".join(f"{value:02x}" for value in mixed)


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def main() -> int:
    args = parse_args()
    executable = Path(args.executable)
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir

    if args.build:
        maybe_build()
    if not executable.exists():
        print(f"No existe el ejecutable: {executable}", file=sys.stderr)
        print("Compila primero con ./build.sh o ejecuta este script con --build.", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    contexts = selected_contexts(args.context)
    cases = [
        (context, scheduler_id, scheduler_name, memory_id, memory_name)
        for context in contexts
        for scheduler_id, scheduler_name in SCHEDULERS
        for memory_id, memory_name in MEMORY_STRATEGIES
    ]
    if args.limit > 0:
        cases = cases[:args.limit]

    combination_rows: list[dict[str, Any]] = []
    process_rows: list[dict[str, Any]] = []

    total = len(cases)
    for index, (context, scheduler_id, scheduler_name, memory_id, memory_name) in enumerate(cases, start=1):
        print(
            f"[{index:02d}/{total:02d}] {context.name} | {scheduler_name} | {memory_name}",
            flush=True,
        )
        row, process_detail, _logs = run_simulation(
            executable,
            context,
            scheduler_id,
            scheduler_name,
            memory_id,
            memory_name,
            seed=args.seed,
            timeout=args.timeout,
        )
        combination_rows.append(row)
        process_rows.extend(process_detail)

    add_scores(combination_rows)

    remove_legacy_outputs(output_dir)
    html_report = generate_html_report(combination_rows, process_rows, output_dir, args.seed)
    html_path = output_dir / "comparison_report.html"
    html_path.write_text(html_report, encoding="utf-8")

    print()
    print(f"Informe HTML: {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
