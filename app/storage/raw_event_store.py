from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.models.event import Event


class RawEventStore:
    """
    Append-only raw event store using JSON Lines files partitioned by day/hour.

    Example path:
      data/raw/2026-02-18/events-20.jsonl
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def append(self, event: Event) -> Path:
        path = self._path_for_timestamp(event.timestamp)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write as one JSON object per line (JSONL)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.model_dump(mode="json"), separators=(",", ":")))
            f.write("\n")

        return path

    def _path_for_timestamp(self, ts: datetime) -> Path:
        day = ts.date().isoformat()
        hour = f"{ts.hour:02d}"
        return self._base_dir / "raw" / day / f"events-{hour}.jsonl"
