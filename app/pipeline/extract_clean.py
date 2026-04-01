from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from app.models.event import Event
from app.pipeline.checkpoint import CheckpointStore, ExtractCleanCheckpoint

_RAW_FILE_RE = re.compile(r"^events-(\d{2})\.jsonl$")


@dataclass(frozen=True)
class RawPartition:
    day: str
    hour: int
    path: Path


class ExtractCleanResult(BaseModel):
    processed_lines: int = 0
    written_clean: int = 0
    invalid_json: int = 0
    invalid_event: int = 0
    last_checkpoint: ExtractCleanCheckpoint | None = None


class ExtractCleanRunner:
    """
    Reads raw JSONL partitions and writes cleaned JSONL partitions.
    Keeps a checkpoint so it only processes new lines.

    Raw input:
      data/raw/YYYY-MM-DD/events-HH.jsonl

    Clean output:
      data/clean/YYYY-MM-DD/clean-HH.jsonl

    Checkpoint:
      data/checkpoints/extract_clean.json
    """

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._raw_root = data_dir / "raw"
        self._clean_root = data_dir / "clean"
        self._checkpoint_store = CheckpointStore(data_dir / "checkpoints" / "extract_clean.json")

    def run_once(self, max_lines: int | None = None) -> ExtractCleanResult:
        result = ExtractCleanResult()
        ckpt = self._checkpoint_store.load()

        partitions = self._list_raw_partitions()
        if not partitions:
            result.last_checkpoint = ckpt
            return result

        for part in partitions:
            start_line = 0

            # Skip partitions before checkpoint
            if ckpt is not None:
                if (part.day, part.hour) < (ckpt.day, ckpt.hour):
                    continue
                if (part.day, part.hour) == (ckpt.day, ckpt.hour):
                    start_line = ckpt.line

            if not part.path.exists():
                continue

            clean_path = self._clean_path(part.day, part.hour)
            clean_path.parent.mkdir(parents=True, exist_ok=True)

            with part.path.open("r", encoding="utf-8") as src, clean_path.open("a", encoding="utf-8") as out:
                for line_idx, line in enumerate(src):
                    if line_idx < start_line:
                        continue

                    if max_lines is not None and result.processed_lines >= max_lines:
                        result.last_checkpoint = ckpt
                        return result

                    result.processed_lines += 1
                    line = line.strip()

                    # advance checkpoint even on blank lines
                    if not line:
                        ckpt = ExtractCleanCheckpoint(day=part.day, hour=part.hour, line=line_idx + 1)
                        self._checkpoint_store.save(ckpt)
                        continue

                    try:
                        obj: Any = json.loads(line)
                    except json.JSONDecodeError:
                        result.invalid_json += 1
                        ckpt = ExtractCleanCheckpoint(day=part.day, hour=part.hour, line=line_idx + 1)
                        self._checkpoint_store.save(ckpt)
                        continue

                    try:
                        event = Event.model_validate(obj)
                    except ValidationError:
                        result.invalid_event += 1
                        ckpt = ExtractCleanCheckpoint(day=part.day, hour=part.hour, line=line_idx + 1)
                        self._checkpoint_store.save(ckpt)
                        continue

                    # Write normalized JSON (UUID/datetime become JSON-friendly in mode="json")
                    out.write(json.dumps(event.model_dump(mode="json"), separators=(",", ":")))
                    out.write("\n")
                    result.written_clean += 1

                    ckpt = ExtractCleanCheckpoint(day=part.day, hour=part.hour, line=line_idx + 1)
                    self._checkpoint_store.save(ckpt)

        result.last_checkpoint = ckpt
        return result

    def _list_raw_partitions(self) -> list[RawPartition]:
        if not self._raw_root.exists():
            return []

        parts: list[RawPartition] = []
        for day_dir in sorted([p for p in self._raw_root.iterdir() if p.is_dir()]):
            day = day_dir.name
            for f in sorted(day_dir.iterdir()):
                if not f.is_file():
                    continue
                m = _RAW_FILE_RE.match(f.name)
                if not m:
                    continue
                hour = int(m.group(1))
                parts.append(RawPartition(day=day, hour=hour, path=f))

        parts.sort(key=lambda p: (p.day, p.hour))
        return parts

    def _clean_path(self, day: str, hour: int) -> Path:
        return self._clean_root / day / f"clean-{hour:02d}.jsonl"