"""Common response models."""

from pydantic import BaseModel


class Pagination(BaseModel):
    """Pagination metadata."""

    page: int
    page_size: int
    total_items: int
    total_pages: int


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: dict  # { code: str, message: str, details?: dict }
