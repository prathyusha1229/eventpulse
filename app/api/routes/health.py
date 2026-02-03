from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """
    Lightweight health endpoint.
    In later days we will expand this to check dependencies (Redis, pipeline lag, etc).
    """
    return {"status": "ok"}
