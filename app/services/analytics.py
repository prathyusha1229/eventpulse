from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from app.storage.aggregate_store import AggregateStore


class AnalyticsService:
    def __init__(self, data_dir: Path) -> None:
        self._store = AggregateStore(data_dir)

    def get_summary(self, days: int) -> dict:  # type: ignore[type-arg]
        date_range = self._date_range(days)
        total = 0
        by_type: dict[str, int] = defaultdict(int)
        daily = []

        for d in date_range:
            agg = self._store.read(d)
            day_total = agg["total_events"] if agg else 0
            day_by_type: dict[str, int] = agg["by_type"] if agg else {}

            daily.append({"date": d, "total": day_total, "by_type": day_by_type})
            total += day_total
            for k, v in day_by_type.items():
                by_type[k] += v

        return {
            "period_days": days,
            "total_events": total,
            "by_type": dict(by_type),
            "daily": daily,
        }

    def get_top_users(self, days: int, limit: int) -> dict:  # type: ignore[type-arg]
        date_range = self._date_range(days)
        merged: dict[str, dict] = {}  # type: ignore[type-arg]

        for d in date_range:
            agg = self._store.read(d)
            if not agg:
                continue
            for uid, udata in agg.get("users", {}).items():
                if uid not in merged:
                    merged[uid] = {"user_id": uid, "total": 0, "by_type": defaultdict(int)}
                merged[uid]["total"] += udata["total"]
                for k, v in udata["by_type"].items():
                    merged[uid]["by_type"][k] += v  # type: ignore[index]

        top = sorted(merged.values(), key=lambda u: u["total"], reverse=True)[:limit]
        for u in top:
            u["by_type"] = dict(u["by_type"])

        return {"users": top}

    def get_user_detail(self, user_id: str, days: int) -> dict:  # type: ignore[type-arg]
        date_range = self._date_range(days)
        total = 0
        by_type: dict[str, int] = defaultdict(int)
        daily = []

        for d in date_range:
            agg = self._store.read(d)
            if agg and user_id in agg.get("users", {}):
                udata = agg["users"][user_id]
                day_total: int = udata["total"]
                day_by_type: dict[str, int] = udata["by_type"]
            else:
                day_total = 0
                day_by_type = {}

            daily.append({"date": d, "total": day_total, "by_type": day_by_type})
            total += day_total
            for k, v in day_by_type.items():
                by_type[k] += v

        return {
            "user_id": user_id,
            "period_days": days,
            "total_events": total,
            "by_type": dict(by_type),
            "daily": daily,
        }

    def _date_range(self, days: int) -> list[str]:
        today = date.today()
        return [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
