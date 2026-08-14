"""
Ascendra — Standard Response Envelope.

Consistent API response format per doc §150.
"""

from typing import Any, Optional

from pydantic import BaseModel


class PaginationMeta(BaseModel):
    """Pagination metadata included in list responses."""
    page: int
    page_size: int
    total: int
    total_pages: int


class ApiResponse(BaseModel):
    """Standard response wrapper: {success, data, meta?}."""
    success: bool = True
    data: Any = None
    meta: Optional[PaginationMeta] = None


def success_response(
    data: Any = None,
    page: int | None = None,
    page_size: int | None = None,
    total: int | None = None,
) -> dict:
    """Build a standard success response dict."""
    resp: dict[str, Any] = {"success": True, "data": data}
    if page is not None and page_size is not None and total is not None:
        total_pages = max(1, (total + page_size - 1) // page_size)
        resp["meta"] = {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        }
    return resp


def paginate_list(items: list, page: int = 1, page_size: int = 20) -> tuple[list, int]:
    """Apply offset pagination to a list and return (sliced_items, total)."""
    total = len(items)
    start = (page - 1) * page_size
    return items[start:start + page_size], total
