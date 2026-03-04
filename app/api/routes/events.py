from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder

from app.core import settings
from app.models.event import Event
from app.schemas.errors import ErrorInfo, ErrorResponse
from app.schemas.ingestion import IngestBatchResponse, IngestOneResponse, RejectedItem
from app.services.ingestion import IngestionService
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
