from __future__ import annotations

from pydantic import BaseModel

from app.models.event import Event


class ListEventsResponse(BaseModel):
    items: list[Event]
    next_cursor: str | None
