from dataclasses import dataclass

@dataclass
class InfoError():
    has_error: bool
    error_code: int = 0
    error_desc: str = ""
    termination_reason = ""
    exit_code: int = 0