from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.models.event import Event
from app.storage.raw_event_store import RawEventStore


class IngestionResult(Event.model_config.__class__):  # type: ignore[misc]
    pass


def parse_event(payload: dict[str, Any]) -> Event:
    # All validation is centralized here
    return Event.model_validate(payload)


class IngestionService:
    def __init__(self, store: RawEventStore) -> None:
        self._store = store

    def ingest_one(self, payload: dict[str, Any]) -> Event:
        event = parse_event(payload)
        self._store.append(event)
        return event

    def ingest_batch(self, payloads: Iterable[dict[str, Any]]) -> dict[str, Any]:
        accepted: list[Event] = []
        rejected: list[dict[str, Any]] = []
        seen_ids: set[UUID] = set()

        for idx, payload in enumerate(payloads):
            try:
                event = parse_event(payload)

                # Basic dedupe inside the batch (same event_id repeated)
                if event.event_id in seen_ids:
                    rejected.append(
                        {
                            "index": idx,
                            "reason": "duplicate event_id in batch",
                            "event_id": str(event.event_id),
                        }
                    )
                    continue

                seen_ids.add(event.event_id)
                self._store.append(event)
                accepted.append(event)
            except ValidationError as e:
                rejected.append({"index": idx, "reason": "validation_error", "details": e.errors()})

        return {
            "accepted": len(accepted),
            "rejected": rejected,
        }
