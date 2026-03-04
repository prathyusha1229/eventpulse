from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.models.event import Event
from app.storage.raw_event_store import RawEventStore


class IngestionService:
    def __init__(self, store: RawEventStore) -> None:
        self._store = store

    def ingest_one(self, event: Event) -> Event:
        self._store.append(event)
        return event

    def ingest_batch(self, payloads: Iterable[dict[str, Any]]) -> tuple[int, list[dict[str, Any]]]:
        accepted_count = 0
        rejected: list[dict[str, Any]] = []
        seen_ids: set[UUID] = set()

        for idx, payload in enumerate(payloads):
            try:
                event = Event.model_validate(payload)

                if event.event_id in seen_ids:
                    rejected.append(
                        {
                            "index": idx,
                            "code": "duplicate_in_batch",
                            "message": "duplicate event_id in batch",
                            "event_id": str(event.event_id),
                        }
                    )
                    continue

                seen_ids.add(event.event_id)
                self._store.append(event)
                accepted_count += 1

            except ValidationError as e:
                rejected.append(
                    {
                        "index": idx,
                        "code": "validation_error",
                        "message": "event validation failed",
                        "details": e.errors(),
                    }
                )

        return accepted_count, rejected
