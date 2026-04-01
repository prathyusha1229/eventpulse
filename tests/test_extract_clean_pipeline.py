
from __future__ import annotations

__all__ = ["ExtractCleanRunner", "ExtractCleanResult"]

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.models.event import Event


@dataclass
class Checkpoint:
    day: str
    hour: int
    line: int


@dataclass
class ExtractCleanResult:
    processed_lines: int = 0
    written_clean: int = 0
    invalid_json: int = 0
    invalid_event: int = 0
    last_checkpoint: Optional[Checkpoint] = None


class ExtractCleanRunner:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.checkpoint_file = data_dir / "checkpoint.json"

    def run_once(self) -> ExtractCleanResult:
        result = ExtractCleanResult()
        # Load checkpoint
        checkpoint = self._load_checkpoint()
        # Find raw files
        raw_dir = self.data_dir / "raw"
        if not raw_dir.exists():
            return result
        # Find the latest day
        days = sorted([d for d in raw_dir.iterdir() if d.is_dir()], key=lambda x: x.name)
        if not days:
            return result
        latest_day = days[-1]
        day_str = latest_day.name
        # Find hours
        hours = sorted([int(f.stem.split('-')[1]) for f in latest_day.glob("events-*.jsonl")])
        if not hours:
            return result
        latest_hour = hours[-1]
        raw_file = latest_day / f"events-{latest_hour}.jsonl"
        clean_dir = self.data_dir / "clean" / day_str
        clean_dir.mkdir(parents=True, exist_ok=True)
        clean_file = clean_dir / f"clean-{latest_hour}.jsonl"
        # If checkpoint is for this file and line == total lines, do nothing
        with open(raw_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        total_lines = len(all_lines)
        if checkpoint and checkpoint.day == day_str and checkpoint.hour == latest_hour:
            if checkpoint.line >= total_lines:
                return result  # already processed
            start_line = checkpoint.line
        else:
            start_line = 0
        # Process from start_line
        lines_to_process = all_lines[start_line:]
        clean_lines = []
        for line in lines_to_process:
            result.processed_lines += 1
            try:
                data = json.loads(line.strip())
            except json.JSONDecodeError:
                result.invalid_json += 1
                continue
            try:
                event = Event(**data)
                clean_lines.append(json.dumps(event.model_dump(mode="json")) + "\n")
                result.written_clean += 1
            except Exception:
                result.invalid_event += 1
        # Write clean
        with open(clean_file, 'a', encoding='utf-8') as f:
            f.writelines(clean_lines)
        # Update checkpoint
        new_checkpoint = Checkpoint(day=day_str, hour=latest_hour, line=start_line + len(lines_to_process))
        self._save_checkpoint(new_checkpoint)
        result.last_checkpoint = new_checkpoint
        return result

    def _load_checkpoint(self) -> Optional[Checkpoint]:
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                data = json.load(f)
            return Checkpoint(**data)
        return None

    def _save_checkpoint(self, checkpoint: Checkpoint):
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint.__dict__, f)