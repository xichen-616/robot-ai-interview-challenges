"""Event-driven, hardware-independent greeting business logic."""

from dataclasses import dataclass, replace
from typing import Optional

from .models import Effect, Event


@dataclass(frozen=True)
class _ReceptionState:
    """Private state for one reception area and its current visit cycle."""

    present: bool = False
    greeted: bool = False
    conversation_active: bool = False
    meeting_active: bool = False
    left_at: Optional[float] = None
    departure_sent: bool = False


class RobotApplication:
    """Turn input events into effects without controlling robot hardware.

    The application intentionally models a single reception area, rather than a
    per-person registry: the task supplies an optional ``person_id`` but does
    not prescribe multi-person behaviour.
    """

    def __init__(self, absence_timeout_s: float = 10.0):
        if absence_timeout_s < 0:
            raise ValueError("absence_timeout_s must be non-negative")
        self._absence_timeout_s = absence_timeout_s
        self._state = _ReceptionState()

    def handle_event(self, event: Event) -> list[Effect]:
        """Apply one event and return only effects newly created for it."""

        if event.event_type == "PERSON_ENTERED":
            return self._handle_person_entered()
        if event.event_type == "PERSON_LEFT":
            self._handle_person_left(event.timestamp)
            return []
        if event.event_type == "CONVERSATION_STARTED":
            self._state = replace(self._state, conversation_active=True)
            return []
        if event.event_type == "CONVERSATION_ENDED":
            self._state = replace(self._state, conversation_active=False)
            return []
        if event.event_type == "MEETING_STARTED":
            self._state = replace(self._state, meeting_active=True)
            return []
        if event.event_type == "MEETING_ENDED":
            self._state = replace(self._state, meeting_active=False)
            return []
        if event.event_type == "TICK":
            return self._handle_tick(event.timestamp)
        return []

    def snapshot(self) -> dict[str, bool | float | None]:
        """Return a fresh, mutable state view that cannot alter application state."""

        return {
            "present": self._state.present,
            "greeted": self._state.greeted,
            "conversation_active": self._state.conversation_active,
            "meeting_active": self._state.meeting_active,
            "left_at": self._state.left_at,
            "departure_sent": self._state.departure_sent,
        }

    def _handle_person_entered(self) -> list[Effect]:
        state = self._state
        is_new_visit = state.departure_sent
        already_greeted = state.greeted and not is_new_visit
        is_suppressed = state.conversation_active or state.meeting_active

        if is_suppressed:
            # Record the entry as handled: ending the suppressed mode must not
            # trigger a delayed greeting.
            self._state = replace(
                state,
                present=True,
                greeted=True,
                left_at=None,
                departure_sent=False,
            )
            return []

        self._state = replace(
            state,
            present=True,
            greeted=True,
            left_at=None,
            departure_sent=False,
        )
        if already_greeted:
            return []
        return [
            Effect("ROBOT_ACTION", "wave_hand", "person_entered"),
            Effect("SPEECH", "欢迎光临", "person_entered"),
        ]

    def _handle_person_left(self, timestamp: float) -> None:
        if self._state.present:
            self._state = replace(self._state, present=False, left_at=timestamp)

    def _handle_tick(self, timestamp: float) -> list[Effect]:
        state = self._state
        if (
            state.present
            or state.left_at is None
            or state.departure_sent
            or timestamp - state.left_at < self._absence_timeout_s
        ):
            return []

        # The timeout is consumed even while an interaction is active. This
        # prevents a prohibited farewell from being emitted after it ends.
        self._state = replace(state, greeted=False, departure_sent=True)
        if state.conversation_active or state.meeting_active:
            return []
        return [Effect("SPEECH", "欢迎下次光临", "absence_timeout")]
