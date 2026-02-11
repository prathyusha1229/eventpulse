from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_EVENT_TYPES: set[str] = {"signup", "page_view", "purchase", "error"}


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: UUID
    type: str = Field(..., min_length=1, max_length=50)
    timestamp: datetime
    user_id: str = Field(..., min_length=1, max_length=64)
    session_id: str | None = Field(default=None, min_length=1, max_length=64)
    properties: dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in ALLOWED_EVENT_TYPES:
            allowed = ", ".join(sorted(ALLOWED_EVENT_TYPES))
            raise ValueError(f"invalid event type '{normalized}'. Allowed: {allowed}")
        return normalized

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        # Require timezone-aware timestamps
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (e.g. '2026-01-29T10:00:00Z')")

        # Disallow far-future timestamps (clock skew / bad clients)
        now = datetime.now(UTC)
        if value > now + timedelta(days=366):
            raise ValueError("timestamp is too far in the future")
        return value

    @field_validator("properties")
    @classmethod
    def validate_properties_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        # Defensive limit: don't allow huge payloads
        if len(value) > 50:
            raise ValueError("properties too large (max 50 keys)")
        return value
