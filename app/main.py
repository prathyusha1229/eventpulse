from fastapi import FastAPI

from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router

app = FastAPI(
    title="EventPulse",
    version="0.1.0",
    description="Event ingestion + analytics backend (no SQL).",
)

app.include_router(health_router)
app.include_router(events_router)
