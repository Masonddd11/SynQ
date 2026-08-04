"""Common response models."""

from app.models.base import CamelModel


class Pagination(CamelModel):
    """Pagination metadata."""

    page: int
    page_size: int
    total_items: int
    total_pages: int


class ErrorResponse(CamelModel):
    """Standard error response."""

    error: dict  # { code: str, message: str, details?: dict }
