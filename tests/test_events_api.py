from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
#from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.settings import settings
from app.main import app


def test_post_events_writes_jsonl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)

    client = TestClient(app)
    payload = {
        "event_id": str(uuid4()),
        "type": "signup",
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "user_id": "user_1",
        "session_id": "sess_1",
        "properties": {"plan": "pro"},
    }

    r = client.post("/events", json=payload)
    assert r.status_code == 201
    assert r.json()["accepted"] == 1

    # Verify file exists and contains one JSON line
    raw_dir = tmp_path / "raw"
    files = list(raw_dir.rglob("events-*.jsonl"))
    assert len(files) == 1

    lines = files[0].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert obj["type"] == "signup"
    assert obj["user_id"] == "user_1"
    assert obj["properties"]["plan"] == "pro"


def test_post_events_batch_accepts_and_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)

    client = TestClient(app)
    good_id = str(uuid4())
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    batch = [
        {
            "event_id": good_id,
            "type": "signup",
            "timestamp": now,
            "user_id": "u1",
            "properties": {},
        },
        {
            "event_id": good_id,
            "type": "signup",
            "timestamp": now,
            "user_id": "u1",
            "properties": {},
        },  # duplicate
        {
            "event_id": "not-a-uuid",
            "type": "signup",
            "timestamp": now,
            "user_id": "u2",
            "properties": {},
        },  # invalid
    ]

    r = client.post("/events/batch", json=batch)
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] == 1
    assert len(body["rejected"]) == 2
