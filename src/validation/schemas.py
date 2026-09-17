from dataclasses import dataclass, field
from typing import List, Dict, Any

REQUIRED_FIELDS = [
    "vehicle_id",
    "timestamp",
    "speed",
    "battery_level",
    "temperature",
    "fault_code",
]


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)
    normalized_event: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchValidationResult:
    valid_events: List[Dict[str, Any]]
    invalid_events: List[Dict[str, Any]]
    invalid_reasons: List[str]
