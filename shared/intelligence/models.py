from dataclasses import dataclass

@dataclass
class OperationalSignal:
    signal_type: str
    severity: str
    task_name: str
    message: str