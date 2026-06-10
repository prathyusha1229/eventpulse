"""Generate realistic sample events and run both pipeline stages."""

from __future__ import annotations

import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core import settings
from app.models.event import Event
from app.pipeline.aggregate import AggregateRunner
from app.pipeline.extract_clean import ExtractCleanRunner
from app.storage.raw_event_store import RawEventStore

USERS = [f"user_{i:03d}" for i in range(1, 21)]
EVENT_WEIGHTS = [("page_view", 55), ("error", 20), ("signup", 10), ("purchase", 15)]
PAGES = ["/home", "/pricing", "/docs", "/login", "/signup", "/dashboard", "/settings", "/blog"]
ERROR_CODES = ["500", "404", "403", "timeout", "null_reference", "crash"]
REFERRERS = ["google", "direct", "twitter", "github", "email", ""]
PLANS = ["basic", "pro", "enterprise"]


def random_event(ts: datetime) -> Event:
    etype = random.choices(
        [t for t, _ in EVENT_WEIGHTS],
        weights=[w for _, w in EVENT_WEIGHTS],
    )[0]
    uid = random.choice(USERS)

    props: dict = {}
    if etype == "page_view":
        props = {"page": random.choice(PAGES), "referrer": random.choice(REFERRERS)}
    elif etype == "error":
        props = {"code": random.choice(ERROR_CODES), "page": random.choice(PAGES)}
    elif etype == "purchase":
        props = {
            "amount": round(random.uniform(9.99, 299.99), 2),
            "plan": random.choice(PLANS),
            "currency": "USD",
        }
    elif etype == "signup":
        props = {"plan": random.choice(PLANS), "referrer": random.choice(REFERRERS)}

    return Event(
        event_id=uuid4(),
        type=etype,
        timestamp=ts,
        user_id=uid,
        session_id=str(uuid4())[:8],
        properties=props,
    )


def main() -> None:
    store = RawEventStore(settings.data_dir)
    now = datetime.now(UTC)
    total = 0

    print("Seeding raw events for the last 7 days...")
    for day_offset in range(6, -1, -1):
        base = now - timedelta(days=day_offset)
        n_events = random.randint(180, 350)
        for _ in range(n_events):
            hour = random.randint(0, 23)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            ts = base.replace(hour=hour, minute=minute, second=second, microsecond=0)
            store.append(random_event(ts))
            total += 1
        print(f"  {base.date().isoformat()}  {n_events} events")

    print(f"\nTotal raw events written: {total}")

    print("\nRunning extract-clean pipeline...")
    ec_result = ExtractCleanRunner(settings.data_dir).run_once()
    print(f"  Lines processed : {ec_result.processed_lines}")
    print(f"  Clean events    : {ec_result.written_clean}")
    print(f"  Invalid JSON    : {ec_result.invalid_json}")
    print(f"  Invalid events  : {ec_result.invalid_event}")

    print("\nRunning aggregate pipeline...")
    agg_result = AggregateRunner(settings.data_dir).run_once()
    print(f"  Days aggregated : {agg_result.days_processed}")
    print(f"  Total events    : {agg_result.total_events}")

    print("\nDone! Start the dashboard:")
    print("  uvicorn app.main:app --reload")
    print("  Open http://localhost:8000")


if __name__ == "__main__":
    main()
