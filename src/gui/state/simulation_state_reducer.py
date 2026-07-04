from __future__ import annotations

from typing import Any

from gui.domain.models import TOTAL_MEMORY_KB
from gui.mappers.process_mapper import ProcessMapper
from gui.state.simulation_session_store import SimulationSessionStore


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
