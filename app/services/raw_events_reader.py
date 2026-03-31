from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.models.event import Event
from app.storage.raw_event_store import RawEventStore


@dataclass(frozen=True)
class Cursor:
    day: str
    hour: int
    line: int


def _encode_cursor(c: Cursor) -> str:
    raw = json.dumps({"day": c.day, "hour": c.hour, "line": c.line}, separators=(",", ":")).encode(
        "utf-8"
    )
    token = base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")
    return token


def _decode_cursor(token: str) -> Cursor:
    try:
        padded = token + ("=" * (-len(token) % 4))
        raw = base64.urlsafe_b64decode(padded.encode("utf-8"))
        obj = json.loads(raw)
    except Exception as e:
        raise ValueError("cursor is not valid base64/json") from e

    if not isinstance(obj, dict):
        raise ValueError("cursor payload is not an object")

    day = obj.get("day")
    hour = obj.get("hour")
    line = obj.get("line")

    if not isinstance(day, str):
        raise ValueError("cursor.day must be a string")
    if not isinstance(hour, int) or not (0 <= hour <= 23):
        raise ValueError("cursor.hour must be an int in [0, 23]")
    if not isinstance(line, int) or line < 0:
        raise ValueError("cursor.line must be a non-negative int")

    return Cursor(day=day, hour=hour, line=line)


def _floor_to_hour(ts: datetime) -> datetime:
    return ts.replace(minute=0, second=0, microsecond=0)


class RawEventsReader:
    """
    Reads raw events back out of JSONL log files with:
      - time window scan (from/to)
      - filtering (type, user_id)
      - cursor pagination (day+hour+line)
    """

    def __init__(self, store: RawEventStore) -> None:
        self._store = store

    def list_events(
        self,
        start: datetime,
        end: datetime,
        event_type: str | None,
        user_id: str | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[Event], str | None]:
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("start/end must be timezone-aware")
        if start > end:
            raise ValueError("start must be <= end")

        cursor_state: Cursor | None = _decode_cursor(cursor) if cursor else None

        start_hour = _floor_to_hour(start)
        end_hour = _floor_to_hour(end)

        # If cursor is provided, jump scan start to that hour
        if cursor_state is not None:
            cursor_hour_dt = datetime.fromisoformat(
                f"{cursor_state.day}T{cursor_state.hour:02d}:00:00+00:00"
            )
            if cursor_hour_dt > start_hour:
                start_hour = cursor_hour_dt

        items: list[Event] = []
        next_cursor: str | None = None

        current = start_hour
        while current <= end_hour:
            day = current.date().isoformat()
            hour = current.hour
            file_path = self._raw_file_path(day, hour)

            if file_path.exists():
                start_line = 0
                if (
                    cursor_state is not None
                    and cursor_state.day == day
                    and cursor_state.hour == hour
                ):
                    start_line = cursor_state.line

                with file_path.open("r", encoding="utf-8") as f:
                    for line_idx, line in enumerate(f):
                        if line_idx < start_line:
                            continue

                        line = line.strip()
                        if not line:
                            continue

                        try:
                            obj: Any = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        try:
                            event = Event.model_validate(obj)
                        except ValidationError:
                            # If somehow corrupted data gets in, skip it (raw log is append-only).
                            continue

                        if event.timestamp < start or event.timestamp > end:
                            continue
                        if event_type is not None and event.type != event_type:
                            continue
                        if user_id is not None and event.user_id != user_id:
                            continue

                        items.append(event)

                        # Cursor points to the next line in the same file
                        next_cursor = _encode_cursor(Cursor(day=day, hour=hour, line=line_idx + 1))

                        if len(items) >= limit:
                            return items, next_cursor

            current = current + timedelta(hours=1)

        # If we scanned the whole range without hitting limit, there is no next page
        return items, None

    def _raw_file_path(self, day: str, hour: int) -> Path:
        # Mirror RawEventStore partitioning: data/raw/YYYY-MM-DD/events-HH.jsonl
        return self._store._base_dir / "raw" / day / f"events-{hour:02d}.jsonl"  # noqa: SLF001
