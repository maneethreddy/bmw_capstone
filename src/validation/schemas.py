"""Telemetry event schemas and validation result dataclasses.

Defines the :data:`REQUIRED_FIELDS` constant and two dataclasses used
throughout the validation layer:

- :class:`ValidationResult` — result of validating a single event.
- :class:`BatchValidationResult` — aggregated result of validating a
  collection of events.
"""

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
    """Outcome of validating a single telemetry event.

    Attributes:
        valid: ``True`` when the event passed all validation rules.
        errors: List of human-readable error messages (empty when valid).
        normalized_event: The normalised event dictionary (empty dict
            when validation failed).
    """

    valid: bool
    errors: List[str] = field(default_factory=list)
    normalized_event: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchValidationResult:
    """Aggregated outcome of validating a batch of telemetry events.

    Attributes:
        valid_events: List of events that passed all validation rules
            (normalised).
        invalid_events: List of events that failed one or more rules
            (original, un-normalised).
        invalid_reasons: Flat list of all error messages from the
            invalid events.
    """

    valid_events: List[Dict[str, Any]]
    invalid_events: List[Dict[str, Any]]
    invalid_reasons: List[str]
