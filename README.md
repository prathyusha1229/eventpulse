# EventPulse

A self-hosted behavioral analytics platform built to understand data pipelines end-to-end. Tracks user events (page views, clicks, errors, purchases), processes them through a three-stage pipeline, and serves a live dashboard.

 EventPulse demonstrates the full journey from raw event ingestion to pre-aggregated analytics — the same pattern used in production systems like Segment, Mixpanel, or Amplitude, but built from first principles without a database.

---

## Architecture

```
Client / SDK
     │
     ▼
┌─────────────────────┐
│   Ingest API        │  POST /events        (single or batch)
│   FastAPI           │  Validates, dedupes
└────────┬────────────┘
         │ writes JSONL
         ▼
┌─────────────────────┐
│   Raw Store         │  data/raw/YYYY-MM-DD/events-HH.jsonl
│   Append-only       │  Partitioned by day + hour
└────────┬────────────┘
         │
         ▼  (run: python scripts/run_extract_clean.py)
┌─────────────────────┐
│  Extract-Clean      │  Validates & normalizes each event
│  Pipeline           │  Skips invalid JSON / bad events
└────────┬────────────┘
         │ writes JSONL
         ▼
┌─────────────────────┐
│   Clean Store       │  data/clean/YYYY-MM-DD/clean-HH.jsonl
└────────┬────────────┘
         │
         ▼  (run: python scripts/run_aggregate.py)
┌─────────────────────┐
│  Aggregate          │  Counts by type, by hour, per user
│  Pipeline           │  Idempotent — re-run safely
└────────┬────────────┘
         │ writes JSON
         ▼
┌─────────────────────┐
│  Aggregate Store    │  data/aggregates/YYYY-MM-DD.json
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Analytics API      │  GET /analytics/summary
│  FastAPI            │  GET /analytics/users
└────────┬────────────┘  GET /analytics/users/{id}
         │
         ▼
┌─────────────────────┐
│  Dashboard          │  http://localhost:8000
│  Chart.js + HTML    │  Auto-refreshes every 30s
└─────────────────────┘
```

**No database.** Storage is plain JSONL files partitioned by day and hour — fast to append, easy to replay, zero infrastructure overhead.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Seed sample data + run both pipeline stages
python scripts/seed_data.py

# 3. Start the server
uvicorn app.main:app --reload

# 4. Open the dashboard
open http://localhost:8000
```

Or with Docker:

```bash
docker compose up --build
# then: python scripts/seed_data.py  (run once to generate data)
```

---

## API Reference

### Event Ingestion

| Method | Path           | Description                              |
|--------|----------------|------------------------------------------|
| POST   | `/events`      | Ingest a single event (returns 201)      |
| POST   | `/events/batch`| Ingest up to 500 events                  |
| GET    | `/events`      | List events with filters + cursor paging |

**Event payload:**
```json
{
  "event_id": "uuid",
  "type": "page_view | error | signup | purchase",
  "timestamp": "2026-06-09T14:30:00Z",
  "user_id": "user_001",
  "session_id": "optional",
  "properties": {}
}
```

### Analytics

| Method | Path                           | Description                         |
|--------|--------------------------------|-------------------------------------|
| GET    | `/analytics/summary?days=7`    | Total + daily breakdown by type     |
| GET    | `/analytics/users?days=7`      | Top users ranked by event count     |
| GET    | `/analytics/users/{id}?days=7` | Per-user breakdown over time        |

### Other

| Method | Path      | Description        |
|--------|-----------|--------------------|
| GET    | `/`       | Dashboard UI       |
| GET    | `/health` | Health check       |
| GET    | `/docs`   | Swagger UI (OpenAPI) |

---

## Pipeline Stages

### 1. Ingest → Raw
`POST /events` validates each event with Pydantic and appends it as a JSON line to a partition file. Validation rejects unknown event types, naive timestamps, and oversized property bags.

### 2. Extract-Clean
`python scripts/run_extract_clean.py` reads raw JSONL line-by-line, re-validates every event, normalizes UUIDs and datetimes, and writes clean JSONL. A file-based checkpoint ensures only new lines are processed on each run — safe to run as a cron job.

### 3. Aggregate
`python scripts/run_aggregate.py` reads clean JSONL and produces per-day aggregate files:
```json
{
  "date": "2026-06-09",
  "total_events": 312,
  "by_type": { "page_view": 171, "error": 62, "signup": 31, "purchase": 48 },
  "by_hour": { "00": 12, "01": 8, "..." : "..." },
  "users": {
    "user_001": { "user_id": "user_001", "total": 29, "by_type": { "..." : "..." } }
  }
}
```

---

## Tech Stack

| Layer      | Technology                            |
|------------|---------------------------------------|
| API        | FastAPI 0.115, Pydantic v2, Uvicorn   |
| Storage    | Append-only JSONL (no SQL/NoSQL)      |
| Frontend   | Vanilla JS + Chart.js (no build step) |
| Testing    | pytest, pytest-asyncio, httpx         |
| Quality    | Ruff (lint+format), MyPy strict mode  |
| Container  | Docker + Docker Compose               |

---

## Project Layout

```
eventpulse/
├── app/
│   ├── api/routes/        # events.py, analytics.py, health.py
│   ├── models/            # event.py  (Pydantic domain model)
│   ├── schemas/           # ingestion.py, events_read.py, analytics.py
│   ├── services/          # ingestion.py, raw_events_reader.py, analytics.py
│   ├── storage/           # raw_event_store.py, aggregate_store.py
│   └── pipeline/          # extract_clean.py, aggregate.py, checkpoint.py
├── frontend/
│   └── index.html         # Dashboard (Chart.js, no build step)
├── scripts/
│   ├── seed_data.py        # Generate sample events + run both pipelines
│   ├── run_extract_clean.py
│   └── run_aggregate.py
├── tests/
├── Dockerfile
└── docker-compose.yml
```

---

## What I Learned / Design Decisions

- **JSONL + partitioning** — Append-only files partitioned by day/hour give you write throughput without a database. A real system would swap this for Kafka → S3/GCS, but the pattern is identical.
- **Checkpoint-based pipelines** — Each pipeline stage records where it stopped, making re-runs idempotent. This is the same pattern as Kafka consumer offsets or Flink checkpoints.
- **Cursor pagination** — The read API encodes `{day, hour, line}` as a base64 cursor rather than using `OFFSET`, which stays fast regardless of dataset size.
- **Pre-aggregation** — The analytics API reads pre-computed aggregates (O(days)), not raw data (O(events)). This is why dashboards at scale use a separate aggregation job rather than ad-hoc queries.
