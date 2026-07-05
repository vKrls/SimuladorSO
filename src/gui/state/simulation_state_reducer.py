from __future__ import annotations

from typing import Any

from gui.domain.models import TOTAL_MEMORY_KB
from gui.mappers.process_mapper import ProcessMapper
from gui.state.simulation_session_store import SimulationSessionStore


MEMORY_HISTORY_LIMIT = 2000


class SimulationStateReducer:
    def __init__(self, process_mapper: ProcessMapper):
        self.process_mapper = process_mapper

    def apply(
        self,
        algorithm: str,
        events: list[dict[str, Any]],
        store: SimulationSessionStore,
    ) -> dict[str, Any]:
        state = store.ensure_state(algorithm)

        for event in events:
            event_type = event.get("type")
            if event_type == "state":
                state["snapshot"] = {
                    "current_time": event.get("current_time", 0.0),
                    "simulator_state": event.get("simulator_state", 1),
                    "cpu_busy": event.get("cpu_busy", False),
                    "quantum": event.get("config", {}).get("quantum", 0.0),
                    "switch_cost": event.get("config", {}).get("switch_cost", 0.0),
                    "sim_speed": event.get("config", {}).get("sim_speed", 5),
                    "snapshot_interval_ms": event.get("config", {}).get(
                        "snapshot_interval_ms",
                        100,
                    ),
                    "block_size_kb": event.get("memory", {}).get(
                        "block_size_kb",
                        4,
                    ),
                }
                state["state_event"] = event
                state["memory"] = event.get("memory", {})
                state["gantt"] = event.get("gantt", {})
                state["stats"] = event.get("stats", {})
                processes_by_pid = {
                    int(process.get("pid", -1)): process
                    for process in event.get("processes", [])
                }
                running_pid = event.get("running_pid")
                state["running"] = (
                    processes_by_pid.get(int(running_pid))
                    if running_pid is not None
                    else None
                )
                state["queues"] = event.get("queues", {})
                self._append_memory_history(state, event)
            elif event_type == "snapshot":
                state["snapshot"] = event
            elif event_type == "queue":
                self._apply_queue_event(state, event)
            elif event_type == "running":
                state["running"] = event.get("process")
                running = state["running"]
                if running is not None:
                    self._remove_pid_from_queues(state, int(running["pid"]))
            elif event_type == "memory":
                state["memory"] = event
            elif event_type == "gantt":
                state["gantt"] = event

        self._rebuild_processes(algorithm, state, store)
        state["memory_map"] = self._build_memory_map(algorithm, state, store)
        if not state.get("stats"):
            state["stats"] = self._build_stats(algorithm, state, store)
        state["memory_history_summary"] = self._build_memory_history_summary(
            state.get("memory_history", []),
        )
        if any(event.get("type") == "state" for event in events):
            store.reset_random_process_count(algorithm)
        return state

    def _apply_queue_event(
        self,
        state: dict[str, Any],
        event: dict[str, Any],
    ) -> None:
        queue_name = str(event.get("name", ""))
        processes = list(event.get("processes", []))
        for process in processes:
            self._remove_pid_from_queues(
                state,
                int(process["pid"]),
                except_queue=queue_name,
            )
        state["queues"][queue_name] = processes

    def _remove_pid_from_queues(
        self,
        state: dict[str, Any],
        pid: int,
        *,
        except_queue: str | None = None,
    ) -> None:
        for queue_name, processes in state["queues"].items():
            if queue_name == except_queue:
                continue
            state["queues"][queue_name] = [
                process for process in processes
                if int(process["pid"]) != pid
            ]

    def _rebuild_processes(
        self,
        algorithm: str,
        state: dict[str, Any],
        store: SimulationSessionStore,
    ) -> None:
        pcb_by_pid: dict[int, dict[str, Any]] = {}
        state_event = state.get("state_event", {})
        if state_event:
            pcb_by_pid = {
                int(pcb["pid"]): pcb
                for pcb in state_event.get("processes", [])
            }
        else:
            for processes in state["queues"].values():
                if not isinstance(processes, list):
                    continue
                for pcb in processes:
                    if isinstance(pcb, dict):
                        pcb_by_pid[int(pcb["pid"])] = pcb

            running = state.get("running")
            if running is not None:
                pcb_by_pid[int(running["pid"])] = running

        previous_colors = {
            process.pid: process.color
            for process in (
                store.processes_for(algorithm)
                + store.system_processes_for(algorithm)
            )
        }
        rebuilt = [
            self.process_mapper.ui_process_from_pcb(
                pcb,
                previous_colors.get(int(pcb.get("pid", 0))),
                state.get("snapshot", {}),
            )
            for _, pcb in sorted(pcb_by_pid.items())
        ]
        store.set_system_processes(
            algorithm,
            [process for process in rebuilt if process.is_system],
        )
        user_processes = [
            process for process in rebuilt if not process.is_system
        ]
        store.set_processes(algorithm, user_processes)
        if user_processes:
            store.set_next_pid(
                algorithm,
                max(process.pid for process in user_processes) + 1,
            )

    def _build_memory_map(
        self,
        algorithm: str,
        state: dict[str, Any],
        store: SimulationSessionStore,
    ) -> dict[str, Any]:
        memory = state.get("memory", {})
        block_size = int(memory.get("block_size_kb", 4))
        processes = {
            process.pid: process
            for process in (
                store.processes_for(algorithm)
                + store.system_processes_for(algorithm)
            )
        }
        blocks = []
        for block in memory.get("blocks", []):
            raw_owner = block.get("owner_pid")
            owner = int(raw_owner) if raw_owner is not None else -1
            process = processes.get(owner)
            is_system = bool(block.get("is_system", False))
            blocks.append(
                {
                    "base_kb": int(block.get("start_block", 0)) * block_size,
                    "size_kb": int(block.get("length_blocks", 0)) * block_size,
                    "name": process.name if process else str(block.get("owner_name", "Libre")),
                    "color": (
                        "#c77dff"
                        if is_system
                        else process.color if process else "#30363d"
                    ),
                }
            )
        return {
            "total_kb": int(memory.get("total_kb", TOTAL_MEMORY_KB)),
            "free_kb": int(memory.get("free_kb", TOTAL_MEMORY_KB)),
            "os_reserved_kb": int(memory.get("os_reserved_kb", 0)),
            "block_size_kb": block_size,
            "blocks": blocks,
        }

    def _append_memory_history(
        self,
        state: dict[str, Any],
        event: dict[str, Any],
    ) -> None:
        memory = event.get("memory", {})
        if not isinstance(memory, dict):
            return

        sequence = int(event.get("sequence", 0) or 0)
        history = state.setdefault("memory_history", [])
        if history:
            previous_sequence = int(history[-1].get("sequence", 0) or 0)
            if sequence > 0 and sequence == previous_sequence:
                return
            if sequence > 0 and sequence < previous_sequence:
                history.clear()

        block_size_kb = int(memory.get("block_size_kb", 4) or 4)
        total_kb = int(memory.get("total_kb", TOTAL_MEMORY_KB) or TOTAL_MEMORY_KB)
        free_kb = int(memory.get("free_kb", 0) or 0)
        os_reserved_kb = int(memory.get("os_reserved_kb", 0) or 0)
        user_total_kb = max(0, total_kb - os_reserved_kb)
        used_user_kb = max(0, user_total_kb - free_kb)

        free_blocks = [
            int(block.get("length_blocks", 0) or 0) * block_size_kb
            for block in memory.get("blocks", [])
            if block.get("owner_pid") is None
        ]
        largest_free_kb = max(free_blocks, default=0)
        free_holes = len(free_blocks)

        internal_waste_kb = 0
        assigned_kb = 0
        resident_processes = 0
        for pcb in event.get("processes", []):
            if pcb.get("is_system") or not pcb.get("resident"):
                continue
            if str(pcb.get("state", "")) == "TERMINATED":
                continue
            process_memory = pcb.get("memory", {})
            internal_waste_kb += int(process_memory.get("waste_kb", 0) or 0)
            assigned_blocks = int(process_memory.get("assigned_blocks", 0) or 0)
            assigned_kb += assigned_blocks * block_size_kb
            resident_processes += 1

        history.append(
            {
                "sequence": sequence,
                "time": float(event.get("current_time", 0.0) or 0.0),
                "memory_used_pct": self._pct(max(0, total_kb - free_kb), total_kb),
                "user_memory_used_pct": self._pct(used_user_kb, user_total_kb),
                "free_kb": free_kb,
                "free_holes": free_holes,
                "largest_free_kb": largest_free_kb,
                "external_fragmentation_pct": (
                    0.0
                    if free_kb <= 0
                    else (free_kb - largest_free_kb) / free_kb * 100.0
                ),
                "internal_waste_kb": internal_waste_kb,
                "internal_waste_pct": self._pct(internal_waste_kb, assigned_kb),
                "resident_processes": resident_processes,
            }
        )
        if len(history) > MEMORY_HISTORY_LIMIT:
            del history[:-MEMORY_HISTORY_LIMIT]

    def _build_memory_history_summary(
        self,
        history: list[dict[str, Any]],
    ) -> dict[str, float]:
        if not history:
            return {}

        def avg(key: str) -> float:
            return sum(float(sample.get(key, 0.0) or 0.0) for sample in history) / len(history)

        def peak(key: str) -> float:
            return max(float(sample.get(key, 0.0) or 0.0) for sample in history)

        def low(key: str) -> float:
            return min(float(sample.get(key, 0.0) or 0.0) for sample in history)

        return {
            "samples": float(len(history)),
            "avg_external_fragmentation_pct": avg("external_fragmentation_pct"),
            "max_external_fragmentation_pct": peak("external_fragmentation_pct"),
            "avg_free_holes": avg("free_holes"),
            "max_free_holes": peak("free_holes"),
            "avg_largest_free_mb": avg("largest_free_kb") / 1024,
            "min_largest_free_mb": low("largest_free_kb") / 1024,
            "peak_user_memory_used_pct": peak("user_memory_used_pct"),
            "peak_memory_used_pct": peak("memory_used_pct"),
            "avg_internal_waste_mb": avg("internal_waste_kb") / 1024,
            "max_internal_waste_mb": peak("internal_waste_kb") / 1024,
        }

    def _build_stats(
        self,
        algorithm: str,
        state: dict[str, Any],
        store: SimulationSessionStore,
    ) -> dict[str, float]:
        processes = store.processes_for(algorithm)
        finished = [
            process for process in processes
            if process.state == "TERMINATED"
        ]
        current_time = float(state.get("snapshot", {}).get("current_time", 0.0))
        gantt_time = sum(
            float(segment.get("duration", 0.0))
            for segment in state.get("gantt", {}).get("segments", [])
            if segment.get("kind", "PROCESS") == "PROCESS"
        )

        def average(attribute: str) -> float:
            if not finished:
                return 0.0
            return sum(
                float(getattr(process, attribute) or 0.0)
                for process in finished
            ) / len(finished)

        return {
            "avg_ready_time": average("ready_time"),
            "avg_turnaround": average("turnaround_time"),
            "avg_response": average("response_time"),
            "throughput": len(finished) / current_time if current_time > 0 else 0.0,
            "cpu_util": gantt_time / current_time * 100.0 if current_time > 0 else 0.0,
            "total_time": current_time,
        }

    def _pct(self, numerator: float, denominator: float) -> float:
        if denominator <= 0:
            return 0.0
        return numerator / denominator * 100.0
