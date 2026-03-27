from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseBase(BaseModel):
    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DataResponse(ResponseBase, Generic[T]):
    data: T | None = None


class PaginatedResponse(ResponseBase, Generic[T]):
    data: list[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0


def success_response(data: Any = None, message: str = "OK") -> dict:
    return {
        "success": True,
        "code": "SUCCESS",
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }


def error_response(code: str, message: str, data: Any = None) -> dict:
    return {
        "success": False,
        "code": code,
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }


def paginated_response(
    data: list[Any],
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
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "timestamp": datetime.utcnow().isoformat(),
    }
