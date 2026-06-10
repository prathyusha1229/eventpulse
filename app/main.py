from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.error_handlers import register_exception_handlers
from app.api.routes.analytics import router as analytics_router
from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router

app = FastAPI(
    title="EventPulse",
    version="0.1.0",
    description="Behavioral analytics platform — ingest events, run pipelines, explore a live dashboard.",
)

register_exception_handlers(app)

app.include_router(health_router)
app.include_router(events_router)
app.include_router(analytics_router)

_FRONTEND = Path(__file__).parent.parent / "frontend"


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(_FRONTEND / "index.html")
