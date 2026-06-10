from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core import settings
from app.schemas.analytics import SummaryResponse, TopUsersResponse, UserDetailResponse
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_analytics_service() -> AnalyticsService:
    return AnalyticsService(settings.data_dir)


AnalyticsSvcDep = Annotated[AnalyticsService, Depends(get_analytics_service)]


@router.get("/summary", response_model=SummaryResponse)
def get_summary(
    svc: AnalyticsSvcDep,
    days: int = Query(7, ge=1, le=90),
) -> SummaryResponse:
    return SummaryResponse(**svc.get_summary(days))


@router.get("/users", response_model=TopUsersResponse)
def get_top_users(
    svc: AnalyticsSvcDep,
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(10, ge=1, le=100),
) -> TopUsersResponse:
    return TopUsersResponse(**svc.get_top_users(days, limit))


@router.get("/users/{user_id}", response_model=UserDetailResponse)
def get_user_detail(
    user_id: str,
    svc: AnalyticsSvcDep,
    days: int = Query(7, ge=1, le=90),
) -> UserDetailResponse:
    return UserDetailResponse(**svc.get_user_detail(user_id, days))
