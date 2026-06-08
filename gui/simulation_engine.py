from __future__ import annotations

import json
from collections import deque
from math import ceil
from typing import Any, Callable

TOTAL_MEMORY_KB = 4096
EPSILON = 1e-9


class LocalSimulationEngine:
    def simulate(self, payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
        algorithm = str(payload.get("algorithm", "fcfs"))
        processes = self._prepare_processes(payload.get("processes", []))
        self._allocate_memory(processes)

        label = self._algorithm_label(algorithm)
        events: list[dict[str, Any]] = [
            {"type": "log", "level": "INFO", "message": f"Simulación {label} iniciada."},
            {"type": "log", "level": "INFO", "message": f"{len(processes)} proceso(s) cargado(s)."},
        ]

        segments = self._schedule(algorithm, processes)
        events.extend(self._segment_logs(segments))

        process_events = [self._process_event(process) for process in sorted(processes, key=lambda item: item["pid"])]
        events.extend(process_events)
        events.append({"type": "memory_map", "total_kb": TOTAL_MEMORY_KB, "blocks": self._memory_blocks(processes)})
        events.append({"type": "gantt", "segments": segments})
        completed = [self._stats_process(process) for process in sorted(processes, key=lambda item: item["pid"])]
        events.append({"type": "stats", "processes": completed, "summary": self._summary(completed)})
        events.append({"type": "log", "level": "DONE", "message": "Simulación completada."})

        stdout = "\n".join(json.dumps(event, separators=(",", ":"), ensure_ascii=False) for event in events)
        return stdout, events

    def _prepare_processes(self, raw_processes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        processes: list[dict[str, Any]] = []
        for raw in raw_processes:
            burst = max(0.0, float(raw.get("burst_time", 0.0)))
            pid = int(raw.get("pid", len(processes) + 1))
            processes.append({
                "pid": pid,
                "name": str(raw.get("name") or f"P{pid}"),
                "burst_time": burst,
                "remaining_time": burst,
                "memory_kb": max(0, int(raw.get("memory_kb", 0))),
                "arrival_time": max(0.0, float(raw.get("arrival_time", 0.0))),
                "priority": int(raw.get("priority", 0)),
                "quantum": max(0.1, float(raw.get("quantum") or 1.0)),
                "color": str(raw.get("color") or "#00d4ff"),
                "start_time": None,
                "finish_time": None,
                "response_time": None,
                "waiting_time": 0.0,
                "turnaround_time": 0.0,
                "segments_count": 0,
                "memory_base": 0,
                "memory_limit": 0,
                "assigned_blocks": 0,
                "waste_kb": 0,
            })
        return processes

    def _allocate_memory(self, processes: list[dict[str, Any]]) -> None:
        base = 0
        for process in sorted(processes, key=lambda item: item["pid"]):
            blocks = ceil(process["memory_kb"] / 4) if process["memory_kb"] else 0
            allocated = blocks * 4
            limit = min(TOTAL_MEMORY_KB, base + allocated)
            process["memory_base"] = base
            process["memory_limit"] = limit
            process["assigned_blocks"] = blocks
            process["waste_kb"] = max(0, allocated - process["memory_kb"])
            base = limit

    def _schedule(self, algorithm: str, processes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not processes:
            return []
        if algorithm == "sjf_preemptive":
            return self._schedule_preemptive(processes, lambda process: (process["remaining_time"], process["arrival_time"], process["pid"]))
        if algorithm == "priority_preemptive":
            return self._schedule_preemptive(processes, lambda process: (process["priority"], process["arrival_time"], process["pid"]))
        if algorithm == "sjf_nonpreemptive":
            return self._schedule_nonpreemptive(processes, lambda process: (process["burst_time"], process["arrival_time"], process["pid"]))
        if algorithm == "priority_nonpreemptive":
            return self._schedule_nonpreemptive(processes, lambda process: (process["priority"], process["arrival_time"], process["pid"]))
        if algorithm == "round_robin":
            return self._schedule_round_robin(processes)
        return self._schedule_nonpreemptive(processes, lambda process: (process["arrival_time"], process["pid"]))

    def _schedule_nonpreemptive(self, processes: list[dict[str, Any]], key: Callable[[dict[str, Any]], tuple]) -> list[dict[str, Any]]:
        pending = set(process["pid"] for process in processes)
        by_pid = {process["pid"]: process for process in processes}
        current = min(process["arrival_time"] for process in processes)
        segments: list[dict[str, Any]] = []

        while pending:
            available = [by_pid[pid] for pid in pending if by_pid[pid]["arrival_time"] <= current + EPSILON]
            if not available:
                current = min(by_pid[pid]["arrival_time"] for pid in pending)
                available = [by_pid[pid] for pid in pending if by_pid[pid]["arrival_time"] <= current + EPSILON]

            process = min(available, key=key)
            start = max(current, process["arrival_time"])
            duration = process["remaining_time"]
            self._mark_start(process, start)
            self._add_segment(segments, process, start, duration)
            current = start + duration
            process["remaining_time"] = 0.0
            self._mark_finish(process, current)
            pending.remove(process["pid"])

        return segments

    def _schedule_preemptive(self, processes: list[dict[str, Any]], key: Callable[[dict[str, Any]], tuple]) -> list[dict[str, Any]]:
        current = min(process["arrival_time"] for process in processes)
        completed = 0
        segments: list[dict[str, Any]] = []

        while completed < len(processes):
            available = [
                process for process in processes
                if process["arrival_time"] <= current + EPSILON and process["remaining_time"] > EPSILON
            ]
            if not available:
                current = min(
                    process["arrival_time"] for process in processes
                    if process["remaining_time"] > EPSILON
                )
                continue

            process = min(available, key=key)
            next_arrival = self._next_arrival_after(processes, current)
            run_for = min(1.0, process["remaining_time"])
            if next_arrival is not None and current + run_for > next_arrival:
                run_for = max(EPSILON, next_arrival - current)

            self._mark_start(process, current)
            self._add_segment(segments, process, current, run_for)
            process["remaining_time"] = max(0.0, process["remaining_time"] - run_for)
            current += run_for

            if process["remaining_time"] <= EPSILON:
                process["remaining_time"] = 0.0
                self._mark_finish(process, current)
                completed += 1

        return segments

    def _schedule_round_robin(self, processes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ordered = sorted(processes, key=lambda process: (process["arrival_time"], process["pid"]))
        ready: deque[dict[str, Any]] = deque()
        current = ordered[0]["arrival_time"]
        index = 0
        completed = 0
        segments: list[dict[str, Any]] = []

        while completed < len(ordered):
            while index < len(ordered) and ordered[index]["arrival_time"] <= current + EPSILON:
                ready.append(ordered[index])
                index += 1

            if not ready:
                current = ordered[index]["arrival_time"]
                continue

            process = ready.popleft()
            duration = min(process["quantum"], process["remaining_time"])
            self._mark_start(process, current)
            self._add_segment(segments, process, current, duration)
            process["remaining_time"] = max(0.0, process["remaining_time"] - duration)
            current += duration

            while index < len(ordered) and ordered[index]["arrival_time"] <= current + EPSILON:
                ready.append(ordered[index])
                index += 1

            if process["remaining_time"] > EPSILON:
                ready.append(process)
            else:
                process["remaining_time"] = 0.0
                self._mark_finish(process, current)
                completed += 1

        return segments

    def _mark_start(self, process: dict[str, Any], start: float) -> None:
        if process["start_time"] is None:
            process["start_time"] = start
            process["response_time"] = max(0.0, start - process["arrival_time"])

    def _mark_finish(self, process: dict[str, Any], finish: float) -> None:
        process["finish_time"] = finish
        process["turnaround_time"] = finish - process["arrival_time"]
        process["waiting_time"] = max(0.0, process["turnaround_time"] - process["burst_time"])

    def _add_segment(self, segments: list[dict[str, Any]], process: dict[str, Any], start: float, duration: float) -> None:
        if duration <= EPSILON:
            return
        if segments:
            last = segments[-1]
            last_end = float(last["start"]) + float(last["duration"])
            if last.get("pid") == process["pid"] and abs(last_end - start) < EPSILON:
                last["duration"] = float(last["duration"]) + duration
                process["segments_count"] += 1
                return
        segments.append({
            "pid": process["pid"],
            "name": process["name"],
            "color": process["color"],
            "start": round(start, 3),
            "duration": round(duration, 3),
        })
        process["segments_count"] += 1

    def _next_arrival_after(self, processes: list[dict[str, Any]], current: float) -> float | None:
        arrivals = [
            process["arrival_time"] for process in processes
            if process["arrival_time"] > current + EPSILON and process["remaining_time"] > EPSILON
        ]
        return min(arrivals) if arrivals else None

    def _process_event(self, process: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "process_update",
            "pid": process["pid"],
            "state": "TERMINATED",
            "remaining_time": 0.0,
            "assigned_blocks": process["assigned_blocks"],
            "waste_kb": process["waste_kb"],
            "program_counter": process["memory_base"] + int(process["burst_time"] * 100),
            "memory_base": process["memory_base"],
            "memory_limit": process["memory_limit"],
            "progress": 100.0,
            "start_time": process["start_time"],
            "finish_time": process["finish_time"],
            "waiting_time": process["waiting_time"],
            "turnaround_time": process["turnaround_time"],
            "response_time": process["response_time"],
            "interrupts": max(0, int(process["segments_count"]) - 1),
        }

    def _memory_blocks(self, processes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        for process in sorted(processes, key=lambda item: item["memory_base"]):
            blocks.append({
                "pid": process["pid"],
                "name": process["name"],
                "color": process["color"],
                "base_kb": process["memory_base"],
                "size_kb": max(0, process["memory_limit"] - process["memory_base"]),
            })
        return blocks

    def _stats_process(self, process: dict[str, Any]) -> dict[str, Any]:
        return {
            "pid": process["pid"],
            "name": process["name"],
            "arrival_time": process["arrival_time"],
            "burst_time": process["burst_time"],
            "start_time": process["start_time"] or 0.0,
            "finish_time": process["finish_time"] or 0.0,
            "waiting_time": process["waiting_time"],
            "turnaround_time": process["turnaround_time"],
            "response_time": process["response_time"] or 0.0,
            "memory_kb": process["memory_kb"],
        }

    def _summary(self, processes: list[dict[str, Any]]) -> dict[str, float]:
        if not processes:
            return {
                "avg_waiting": 0.0,
                "avg_turnaround": 0.0,
                "avg_response": 0.0,
                "throughput": 0.0,
                "total_time": 0.0,
                "cpu_util": 0.0,
            }

        first_arrival = min(process["arrival_time"] for process in processes)
        total_time = max(process["finish_time"] for process in processes)
        elapsed = max(EPSILON, total_time - first_arrival)
        total_burst = sum(process["burst_time"] for process in processes)
        return {
            "avg_waiting": sum(process["waiting_time"] for process in processes) / len(processes),
            "avg_turnaround": sum(process["turnaround_time"] for process in processes) / len(processes),
            "avg_response": sum(process["response_time"] for process in processes) / len(processes),
            "throughput": len(processes) / elapsed,
            "total_time": total_time,
            "cpu_util": min(100.0, (total_burst / elapsed) * 100),
        }

    def _segment_logs(self, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        logs: list[dict[str, Any]] = []
        for segment in segments:
            logs.append({
                "type": "log",
                "level": "RUN",
                "message": (
                    f"t={float(segment['start']):.1f}: {segment['name']} "
                    f"usa CPU durante {float(segment['duration']):.1f} u.t."
                ),
            })
        return logs

    def _algorithm_label(self, algorithm: str) -> str:
        labels = {
            "fcfs": "FCFS",
            "sjf_preemptive": "SJF apropiativo",
            "sjf_nonpreemptive": "SJF no apropiativo",
            "round_robin": "Round Robin",
            "priority_preemptive": "Prioridades apropiativo",
            "priority_nonpreemptive": "Prioridades no apropiativo",
        }
        return labels.get(algorithm, algorithm.upper())
