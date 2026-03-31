from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.settings import settings
from app.main import app


def _ts(s: str) -> str:

    return s


def test_get_events_filters_and_paginates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    client = TestClient(app)

    base_ts = "2026-02-18T20:00:00Z"
    for i in range(5):
        payload = {
            "event_id": str(uuid4()),
            "type": "signup" if i < 3 else "page_view",
            "timestamp": _ts(base_ts),
            "user_id": "u1" if i % 2 == 0 else "u2",
            "properties": {"i": i},
        }
        r = client.post("/events", json=payload)
        assert r.status_code == 201

    # Read with filter type=signup and limit=2
    r1 = client.get(
        "/events", params={"from": base_ts, "to": base_ts, "type": "signup", "limit": 2}
    )
    assert r1.status_code == 200
    body1 = r1.json()
    assert len(body1["items"]) == 2
    assert body1["next_cursor"] is not None
    assert all(item["type"] == "signup" for item in body1["items"])

    # Next page
    r2 = client.get(
        "/events",
        params={
            "from": base_ts,
            "to": base_ts,
            "type": "signup",
            "limit": 2,
            "cursor": body1["next_cursor"],
        },
    )
    assert r2.status_code == 200
    body2 = r2.json()
    # total signup events were 3, so page2 should return 1
    assert len(body2["items"]) == 1
    assert body2["items"][0]["type"] == "signup"
    assert body2["next_cursor"] is None  # fully scanned range


def test_get_events_invalid_cursor_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    client = TestClient(app)

    r = client.get("/events", params={"cursor": "not-a-real-cursor"})
    assert r.status_code == 400
    body = r.json()
    assert body["error"]["code"] == "invalid_cursor"
