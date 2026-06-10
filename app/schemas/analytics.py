from __future__ import annotations

from pydantic import BaseModel


class DailySummary(BaseModel):
    date: str
    total: int
    by_type: dict[str, int]


class SummaryResponse(BaseModel):
    period_days: int
    total_events: int
    by_type: dict[str, int]
    daily: list[DailySummary]


class UserSummary(BaseModel):
    user_id: str
    total: int
    by_type: dict[str, int]


class TopUsersResponse(BaseModel):
    users: list[UserSummary]


class UserDetailResponse(BaseModel):
    user_id: str
    period_days: int
    total_events: int
    by_type: dict[str, int]
    daily: list[DailySummary]
