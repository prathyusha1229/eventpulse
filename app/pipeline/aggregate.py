from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.storage.aggregate_store import AggregateStore

_CLEAN_FILE_RE = re.compile(r"^clean-(\d{2})\.jsonl$")


class AggregateResult(BaseModel):
    days_processed: int = 0
    total_events: int = 0


class AggregateRunner:
    """
    Reads clean JSONL partitions and writes per-day aggregate JSON files.

    Clean input:      data/clean/YYYY-MM-DD/clean-HH.jsonl
    Aggregate output: data/aggregates/YYYY-MM-DD.json
    """

    def __init__(self, data_dir: Path) -> None:
        self._clean_root = data_dir / "clean"
        self._store = AggregateStore(data_dir)

    def run_once(self) -> AggregateResult:
        result = AggregateResult()
        if not self._clean_root.exists():
            return result

        for day_dir in sorted(p for p in self._clean_root.iterdir() if p.is_dir()):
            day_agg = self._aggregate_day(day_dir)
            if day_agg["total_events"] > 0:
                self._store.write(day_dir.name, day_agg)
                result.days_processed += 1
                result.total_events += day_agg["total_events"]

        return result

    def _aggregate_day(self, day_dir: Path) -> dict:  # type: ignore[type-arg]
        by_type: dict[str, int] = defaultdict(int)
        by_hour: dict[str, int] = defaultdict(int)
        users: dict[str, dict[str, Any]] = {}
        total = 0

        for f in sorted(day_dir.iterdir()):
            m = _CLEAN_FILE_RE.match(f.name)
            if not m:
                continue
            hour = m.group(1)

            with f.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    etype = str(obj.get("type", "unknown"))
                    uid = str(obj.get("user_id", "unknown"))

                    by_type[etype] += 1
                    by_hour[hour] += 1
                    total += 1

                    if uid not in users:
                        users[uid] = {"user_id": uid, "total": 0, "by_type": defaultdict(int)}
                    users[uid]["total"] += 1
                    users[uid]["by_type"][etype] += 1  # type: ignore[index]

        for u in users.values():
            u["by_type"] = dict(u["by_type"])

        return {
            "date": day_dir.name,
            "total_events": total,
            "by_type": dict(by_type),
            "by_hour": dict(by_hour),
            "users": users,
        }
