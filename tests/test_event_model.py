from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.event import Event


def test_event_valid() -> None:
    e = Event(
        event_id=uuid4(),
        type="signup",
        timestamp=datetime.now(UTC),
        user_id="user_123",
        session_id="sess_abc",
        properties={"plan": "pro", "source": "ads"},
    )
    assert e.type == "signup"
    assert e.user_id == "user_123"
    assert e.properties["plan"] == "pro"


def test_event_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Event(
            event_id=uuid4(),
            type="signup",
            timestamp=datetime.now(UTC),
            user_id="user_123",
            properties={},
            unexpected="nope",  # type: ignore[call-arg]
        )


def test_event_rejects_invalid_type() -> None:
    with pytest.raises(ValueError):
        Event(
            event_id=uuid4(),
            type="login",
            timestamp=datetime.now(UTC),
            user_id="user_123",
            properties={},
        )


def test_event_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValueError):
        Event(
            event_id=uuid4(),
            type="signup",
            timestamp=datetime(2026, 1, 1, 10, 0, 0),  # naive datetime
            user_id="user_123",
            properties={},
        )


def test_event_rejects_properties_too_large() -> None:
    too_many = {f"k{i}": i for i in range(51)}
    with pytest.raises(ValueError):
        Event(
            event_id=uuid4(),
            type="signup",
            timestamp=datetime.now(UTC),
            user_id="user_123",
            properties=too_many,
        )
