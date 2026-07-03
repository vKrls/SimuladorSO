from __future__ import annotations

import json
from typing import Any


class SimulatorProtocolParser:
    prefix = "SIM_DATA "

    def parse(self, line: str) -> dict[str, Any] | None:
        if not line.startswith(self.prefix):
            return None
        try:
            return json.loads(line[len(self.prefix):])
        except json.JSONDecodeError:
            return None
