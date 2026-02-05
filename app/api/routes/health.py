from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """
   Helloooooooooooooooooooo
    """
    return {"status": "ok"}
