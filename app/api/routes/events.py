from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.core import settings
from app.services.ingestion import IngestionService
from app.storage.raw_event_store import RawEventStore

router = APIRouter(prefix="/events", tags=["events"])


def get_ingestion_service() -> IngestionService:
    store = RawEventStore(settings.data_dir)
    return IngestionService(store)


@router.post("", status_code=status.HTTP_201_CREATED)
def ingest_event(
    payload: dict[str, Any],
    svc: IngestionService = Depends(get_ingestion_service),  # noqa: B008
) -> dict[str, Any]:
    try:
        event = svc.ingest_one(payload)
        return {"accepted": 1, "event_id": str(event.event_id)}
    except Exception as e:
        # For day 3 keep it simple; later we'll map ValidationError to 422 cleanly.
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("/batch", status_code=status.HTTP_200_OK)
def ingest_events_batch(
    payload: list[dict[str, Any]],
    svc: IngestionService = Depends(get_ingestion_service),  # noqa: B008
) -> dict[str, Any]:
    if len(payload) > 500:
        raise HTTPException(status_code=413, detail="batch too large (max 500 events)")
    return svc.ingest_batch(payload)
