from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AggregateStore:
    """
    Stores per-day aggregates as JSON files.
    Path: data/aggregates/YYYY-MM-DD.json
    """

    def __init__(self, base_dir: Path) -> None:
        self._root = base_dir / "aggregates"

    def write(self, day: str, data: dict[str, Any]) -> None:
        path = self._root / f"{day}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
        tmp.replace(path)

    def read(self, day: str) -> dict[str, Any] | None:
        path = self._root / f"{day}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]

    def list_days(self) -> list[str]:
        if not self._root.exists():
            return []
        return sorted(
            p.stem for p in self._root.glob("*.json") if not p.stem.endswith(".tmp")
        )
