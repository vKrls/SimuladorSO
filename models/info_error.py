from dataclasses import dataclass

@dataclass
class Info_Error():
    has_error: bool = False
    error_code: str = ""
    error_message: str = ""