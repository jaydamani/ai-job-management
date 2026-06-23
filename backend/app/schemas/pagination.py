import base64
from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    next_cursor: Optional[str] = None
    has_more: bool


def encode_cursor(*parts: str) -> str:
    joined = "|".join(parts)
    return base64.urlsafe_b64encode(joined.encode()).decode()


def decode_cursor(cursor: str) -> list:
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        return decoded.split("|")
    except Exception:
        raise ValueError("Invalid cursor")
