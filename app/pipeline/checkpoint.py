from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class ExtractCleanCheckpoint(BaseModel):
    """
    Checkpoint points to the next line to read within a raw partition file:
      day:  YYYY-MM-DD
      hour: 0..23
      line: 0-based line index to start from
    """

    day: str = Field(..., min_length=10, max_length=10)
    hour: int = Field(..., ge=0, le=23)
    line: int = Field(..., ge=0)


class CheckpointStore:
    """
    Small file-based checkpoint store (JSON file).
    Uses atomic write: write temp then replace.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> ExtractCleanCheckpoint | None:
        if not self._path.exists():
            return None
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return ExtractCleanCheckpoint.model_validate(data)

    def save(self, checkpoint: ExtractCleanCheckpoint) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(checkpoint.model_dump(mode="json"), separators=(",", ":")),
            encoding="utf-8",
        )
        tmp.replace(self._path)