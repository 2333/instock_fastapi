from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field
from datetime import datetime


class APIResponse(BaseModel):
    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class PaginatedData(BaseModel):
    items: List[Any] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0


def success(data: Any = None, message: str = "OK") -> dict:
    return {
        "success": True,
        "code": "SUCCESS",
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }


def error(code: str, message: str, data: Any = None) -> dict:
    return {
        "success": False,
        "code": code,
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }


def paginated(
    items: List[Any],
    total: int,
    page: int,
    page_size: int,
    message: str = "OK",
) -> dict:
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return {
        "success": True,
        "code": "SUCCESS",
        "message": message,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }
