from typing import Any

from pydantic import BaseModel, Field


class UserEventTrackRequest(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=50)
    event_data: dict[str, Any] | None = None
    page: str | None = Field(None, max_length=100)
    referrer: str | None = Field(None, max_length=100)


class UserEventTrackResponse(BaseModel):
    status: str = "ok"
