from __future__ import annotations

from typing import Any

from gui.domain.models import PROCESS_COLORS, UiProcess


class ProcessMapper:
    def color_for(self, pid: int) -> str:
        return PROCESS_COLORS[pid % len(PROCESS_COLORS)]

    def apply_gantt_colors(
        self,
        segments: list[dict[str, Any]],
        processes: list[UiProcess],
    ) -> None:
        colors_by_name = {process.name: process.color for process in processes}
        for segment in segments:
            kind = str(segment.get("kind", "PROCESS"))
            if kind == "IDLE":
                segment["color"] = "#30363d"
                continue
            if kind == "CONTEXT_SWITCH":
                segment["color"] = "#f7c59f"
                continue

            pid = int(segment.get("pid", 0))
            name = str(segment.get("name", f"P{pid}"))
            segment["color"] = colors_by_name.get(name, self.color_for(pid))

    def ui_process_from_pcb(
        self,
        pcb: dict[str, Any],
        color: str | None,
        snapshot: dict[str, Any],
    ) -> UiProcess:
        scheduler = pcb.get("scheduler", {})
        memory = pcb.get("memory", {})
        cpu = pcb.get("cpu", {})
        interrupts = pcb.get("interrupts", {})
        io = pcb.get("io", {})
        error = pcb.get("error", {})
        burst = float(scheduler.get("burst_time", 0.0))
        remaining = max(0.0, float(scheduler.get("remaining_time", 0.0)))
        start = float(scheduler.get("start_time", -1.0))
        finish = float(scheduler.get("finish_time", -1.0))
        response = float(scheduler.get("response_time", 0.0))
        pid = int(pcb.get("pid", 0))
        block_size = int(snapshot.get("block_size_kb", 4) if snapshot else 4)
        error_time = float(error.get("occurred_at", -1.0))

        return UiProcess(
            pid=pid,
            name=str(pcb.get("name", f"P{pid}")),
            burst_time=burst,
            memory=int(memory.get("required_kb", 0)),
            arrival_time=float(scheduler.get("arrival_time", 0.0)),
            priority=int(scheduler.get("priority", 0)),
            quantum=float(snapshot.get("quantum", 0.0)),
            state=str(pcb.get("state", "NONE")),
            remaining_time=remaining,
            assigned_blocks=int(memory.get("assigned_blocks", 0)),
            waste_kb=int(memory.get("waste_kb", 0)),
            program_counter=int(cpu.get("program_counter", 0)),
            stack_pointer=int(cpu.get("stack_pointer", 0)),
            memory_base=max(0, int(memory.get("start_block", 0))) * block_size,
            memory_limit=max(0, int(memory.get("limit_block", 0))) * block_size,
            progress=0.0 if burst <= 0 else (burst - remaining) / burst * 100.0,
            start_time=None if start < 0 else start,
            finish_time=None if finish < 0 else finish,
            ready_time=float(scheduler.get("ready_time", 0.0)),
            turnaround_time=float(scheduler.get("turnaround_time", 0.0)),
            response_time=None if start < 0 else response,
            interrupts=int(interrupts.get("total", 0)),
            planned_interrupts=int(interrupts.get("planned", 0)),
            interrupt_history=list(interrupts.get("history", [])),
            interrupt_breakdown=dict(interrupts.get("by_type", {})),
            is_system=bool(pcb.get("is_system", False)),
            resident=bool(pcb.get("resident", False)),
            memory_block_address=str(memory.get("block_address", "0x0")),
            memory_segments=list(memory.get("segments", [])),
            io_device=str(io.get("device", "NONE")),
            io_remaining=max(0.0, float(io.get("remaining_time", 0.0))),
            blocked_time=float(scheduler.get("blocked_time", 0.0)),
            nonresident_time=float(scheduler.get("nonresident_time", 0.0)),
            cpu_time=float(scheduler.get("cpu_time", 0.0)),
            context_switches=int(scheduler.get("context_switches", 0)),
            swap_count=int(pcb.get("swap_count", 0)),
            error_code=str(error.get("code", "")),
            error_description=str(error.get("description", "")),
            error_time=None if error_time < 0 else error_time,
            color=color or self.color_for(pid),
        )
