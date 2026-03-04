from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class IngestOneResponse(BaseModel):
    accepted: int
    event_id: str


class RejectedItem(BaseModel):
    index: int
    code: str
    message: str
    details: Any | None = None
    event_id: str | None = None


class IngestBatchResponse(BaseModel):
    accepted: int
    rejected: list[RejectedItem]
