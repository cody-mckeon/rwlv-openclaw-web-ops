from dataclasses import dataclass

@dataclass
class OperationalSignal:
    rule_name: str
    signal_type: str
    severity: str
    task_name: str
    message: str
