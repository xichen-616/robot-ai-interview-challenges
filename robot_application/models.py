"""Public event and effect models required by the interview task."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Event:
    """An input observed by an adapter such as vision, dialogue, or a timer."""

    event_type: str
    timestamp: float
    person_id: Optional[str] = None


@dataclass(frozen=True)
class Effect:
    """An output intention for a separate robot bridge to execute."""

    effect_type: str
    value: str
    reason: str
