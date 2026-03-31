from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder

from app.core import settings
from app.models.event import Event
from app.schemas.errors import ErrorInfo, ErrorResponse
from app.schemas.events_read import ListEventsResponse
from app.schemas.ingestion import IngestBatchResponse, IngestOneResponse, RejectedItem
from app.services.ingestion import IngestionService
from app.services.raw_events_reader import RawEventsReader
from app.storage.raw_event_store import RawEventStore

router = APIRouter(prefix="/events", tags=["events"])

MAX_BATCH_EVENTS = 500


def get_ingestion_service() -> IngestionService:
    store = RawEventStore(settings.data_dir)
    return IngestionService(store)


# Ruff B008-safe FastAPI dependency injection (no Depends() call in default args)
IngestionSvcDep = Annotated[IngestionService, Depends(get_ingestion_service)]


def http_error(
    status_code: int, code: str, message: str, details: Any | None = None
) -> HTTPException:
    safe_details = jsonable_encoder(details) if details is not None else None
    payload = ErrorResponse(
        error=ErrorInfo(code=code, message=message, details=safe_details)
    ).model_dump(mode="json")
    return HTTPException(status_code=status_code, detail=payload)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=IngestOneResponse)
def ingest_event(event: Event, svc: IngestionSvcDep) -> IngestOneResponse:
    saved = svc.ingest_one(event)
    return IngestOneResponse(accepted=1, event_id=str(saved.event_id))


@router.post("/batch", response_model=IngestBatchResponse)
def ingest_events_batch(payload: list[dict[str, Any]], svc: IngestionSvcDep) -> IngestBatchResponse:
    if len(payload) > MAX_BATCH_EVENTS:
        raise http_error(
            413, "payload_too_large", f"batch too large (max {MAX_BATCH_EVENTS} events)"
        )

    accepted, rejected_raw = svc.ingest_batch(payload)
    rejected = [RejectedItem(**item) for item in rejected_raw]
    return IngestBatchResponse(accepted=accepted, rejected=rejected)


def get_raw_reader() -> RawEventsReader:
    store = RawEventStore(settings.data_dir)
    return RawEventsReader(store)


RawReaderDep = Annotated[RawEventsReader, Depends(get_raw_reader)]


@router.get("", response_model=ListEventsResponse)
def list_events(
    reader: RawReaderDep,
    from_ts: datetime | None = Query(None, alias="from"),
    to_ts: datetime | None = Query(None, alias="to"),
    event_type: str | None = Query(None, alias="type"),
    user_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    cursor: str | None = Query(None),
) -> ListEventsResponse:
    now = datetime.now(UTC)
    start = from_ts or (now - timedelta(hours=24))
    end = to_ts or now

    if start > end:
        raise http_error(400, "invalid_range", "'from' must be <= 'to'")

    try:
        items, next_cursor = reader.list_events(
            start=start,
            end=end,
            event_type=event_type,
            user_id=user_id,
            limit=limit,
            cursor=cursor,
        )
    except ValueError as e:
        raise http_error(400, "invalid_cursor", str(e)) from e

    return ListEventsResponse(items=items, next_cursor=next_cursor)
