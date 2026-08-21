"""Behavioural tests for the public RobotApplication API."""

import pytest

from robot_application.application import RobotApplication
from robot_application.models import Effect, Event


WELCOME_EFFECTS = [
    Effect("ROBOT_ACTION", "wave_hand", "person_entered"),
    Effect("SPEECH", "欢迎光临", "person_entered"),
]
FAREWELL_EFFECTS = [Effect("SPEECH", "欢迎下次光临", "absence_timeout")]


def event(event_type: str, timestamp: float = 0.0) -> Event:
    return Event(event_type, timestamp, person_id="visitor-1")


def test_first_entry_creates_wave_and_welcome() -> None:
    app = RobotApplication()

    assert app.handle_event(event("PERSON_ENTERED")) == WELCOME_EFFECTS


def test_repeated_entry_during_same_presence_creates_no_effect() -> None:
    app = RobotApplication()
    app.handle_event(event("PERSON_ENTERED"))

    assert app.handle_event(event("PERSON_ENTERED", 1)) == []


def test_leaving_does_not_immediately_send_farewell() -> None:
    app = RobotApplication()
    app.handle_event(event("PERSON_ENTERED"))

    assert app.handle_event(event("PERSON_LEFT", 2)) == []


@pytest.mark.parametrize("tick_time", [9, 9.999])
def test_tick_before_timeout_does_not_send_farewell(tick_time: float) -> None:
    app = RobotApplication()
    app.handle_event(event("PERSON_ENTERED"))
    app.handle_event(event("PERSON_LEFT", 0))

    assert app.handle_event(event("TICK", tick_time)) == []


@pytest.mark.parametrize("tick_time", [10, 10.001])
def test_tick_at_or_after_timeout_sends_one_farewell(tick_time: float) -> None:
    app = RobotApplication()
    app.handle_event(event("PERSON_ENTERED"))
    app.handle_event(event("PERSON_LEFT", 0))

    assert app.handle_event(event("TICK", tick_time)) == FAREWELL_EFFECTS


def test_repeated_ticks_send_farewell_only_once() -> None:
    app = RobotApplication()
    app.handle_event(event("PERSON_ENTERED"))
    app.handle_event(event("PERSON_LEFT", 0))
    app.handle_event(event("TICK", 10))

    assert app.handle_event(event("TICK", 11)) == []


def test_short_absence_return_does_not_send_farewell_or_regreet() -> None:
    app = RobotApplication()
    app.handle_event(event("PERSON_ENTERED"))
    app.handle_event(event("PERSON_LEFT", 0))

    assert app.handle_event(event("PERSON_ENTERED", 5)) == []
    assert app.handle_event(event("TICK", 11)) == []


def test_confirmed_departure_allows_a_new_greeting_cycle() -> None:
    app = RobotApplication()
    app.handle_event(event("PERSON_ENTERED"))
    app.handle_event(event("PERSON_LEFT", 0))
    assert app.handle_event(event("TICK", 10)) == FAREWELL_EFFECTS

    assert app.handle_event(event("PERSON_ENTERED", 20)) == WELCOME_EFFECTS


def test_conversation_suppresses_greeting_and_does_not_backfill_it() -> None:
    app = RobotApplication()
    app.handle_event(event("CONVERSATION_STARTED"))

    assert app.handle_event(event("PERSON_ENTERED")) == []
    assert app.handle_event(event("CONVERSATION_ENDED", 1)) == []
    assert app.handle_event(event("PERSON_ENTERED", 2)) == []


def test_meeting_suppresses_greeting_and_does_not_backfill_it() -> None:
    app = RobotApplication()
    app.handle_event(event("MEETING_STARTED"))

    assert app.handle_event(event("PERSON_ENTERED")) == []
    assert app.handle_event(event("MEETING_ENDED", 1)) == []
    assert app.handle_event(event("PERSON_ENTERED", 2)) == []


@pytest.mark.parametrize("mode_started", ["CONVERSATION_STARTED", "MEETING_STARTED"])
def test_active_interaction_suppresses_timeout_farewell_without_backfill(
    mode_started: str,
) -> None:
    app = RobotApplication()
    app.handle_event(event("PERSON_ENTERED"))
    app.handle_event(event("PERSON_LEFT", 0))
    app.handle_event(event(mode_started, 1))

    assert app.handle_event(event("TICK", 10)) == []
    assert app.handle_event(event("CONVERSATION_ENDED", 11)) == []
    assert app.handle_event(event("MEETING_ENDED", 11)) == []
    assert app.handle_event(event("TICK", 12)) == []


def test_snapshot_is_a_defensive_copy() -> None:
    app = RobotApplication()
    app.handle_event(event("PERSON_ENTERED"))
    snapshot = app.snapshot()
    snapshot["present"] = False
    snapshot["left_at"] = 999.0

    assert app.snapshot()["present"] is True
    assert app.snapshot()["left_at"] is None


def test_person_left_is_idempotent_while_already_absent() -> None:
    app = RobotApplication()
    app.handle_event(event("PERSON_ENTERED"))
    app.handle_event(event("PERSON_LEFT", 0))
    app.handle_event(event("PERSON_LEFT", 8))

    assert app.handle_event(event("TICK", 10)) == FAREWELL_EFFECTS


def test_tick_without_a_recorded_departure_has_no_effect() -> None:
    assert RobotApplication().handle_event(event("TICK", 100)) == []


def test_unknown_event_has_no_effect_and_does_not_change_state() -> None:
    app = RobotApplication()
    before = app.snapshot()

    assert app.handle_event(event("UNKNOWN", 1)) == []
    assert app.snapshot() == before


def test_negative_timeout_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        RobotApplication(absence_timeout_s=-0.1)
