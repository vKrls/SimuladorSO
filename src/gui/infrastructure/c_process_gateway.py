from __future__ import annotations

from pathlib import Path
import queue
import subprocess
import threading


class CProcessGateway:
    def __init__(self, executable: Path):
        self.executable = executable
        self._process: subprocess.Popen[str] | None = None
        self._stdout_queue: queue.Queue[str] = queue.Queue()
        self._stderr_queue: queue.Queue[str] = queue.Queue()
        self._reader_threads: list[threading.Thread] = []

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(self) -> None:
        if self.is_running():
            return

        self._stdout_queue = queue.Queue()
        self._stderr_queue = queue.Queue()
        self._reader_threads = []
        self._process = subprocess.Popen(
            [str(self.executable)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._start_reader(self._process.stdout, self._stdout_queue)
        self._start_reader(self._process.stderr, self._stderr_queue)

    def send_command(self, line: str) -> None:
        if not self.is_running() or self._process is None or self._process.stdin is None:
            raise OSError("El proceso C no está ejecutándose.")
        self._process.stdin.write(line + "\n")
        self._process.stdin.flush()

    def read_stdout_lines(self) -> list[str]:
        self._join_readers_if_exited()
        return self._drain(self._stdout_queue)

    def read_stderr_lines(self) -> list[str]:
        self._join_readers_if_exited()
        return self._drain(self._stderr_queue)

    def wait_for_exit(self, timeout: float) -> bool:
        if self._process is None:
            return True
        try:
            self._process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return False
        self._join_reader_threads()
        self._process = None
        return True

    def close(self) -> None:
        if self._process is None:
            return
        if self._process.poll() is None:
            try:
                self._process.terminate()
                self._process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=1)
        self._join_reader_threads()
        self._process = None

    def _start_reader(self, stream, output_queue: queue.Queue[str]) -> None:
        def read_loop() -> None:
            if stream is None:
                return
            for line in stream:
                output_queue.put(line.rstrip("\n"))

        thread = threading.Thread(target=read_loop, daemon=True)
        thread.start()
        self._reader_threads.append(thread)

    def _join_readers_if_exited(self) -> None:
        if self._process is not None and self._process.poll() is not None:
            self._join_reader_threads()

    def _join_reader_threads(self) -> None:
        for thread in self._reader_threads:
            thread.join(timeout=0.1)

    def _drain(self, output_queue: queue.Queue[str]) -> list[str]:
        lines: list[str] = []
        while True:
            try:
                lines.append(output_queue.get_nowait())
            except queue.Empty:
                return lines
