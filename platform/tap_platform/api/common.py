"""Shared API conventions: cursor pagination, RFC 7807 errors, idempotency keys.

All timestamps are UTC ISO 8601 strings; all identifiers are UUIDs serialized
as ``str`` (snake_case field names throughout).
"""

from __future__ import annotations

from typing import Annotated, Generic, TypeVar

from fastapi import Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

T = TypeVar("T")

PROBLEM_CONTENT_TYPE = "application/problem+json"


class Problem(BaseModel):
    """RFC 7807 problem details document."""

    type: str = Field(default="about:blank", description="URI identifying the problem type.")
    title: str = Field(description="Short, human-readable summary.")
    status: int = Field(description="HTTP status code.")
    detail: str | None = Field(default=None, description="Occurrence-specific explanation.")
    instance: str | None = Field(default=None, description="URI of the specific occurrence.")


class ProblemResponse(JSONResponse):
    """JSONResponse with the RFC 7807 media type."""

    media_type = PROBLEM_CONTENT_TYPE


def problem(status: int, title: str, detail: str | None = None, type_: str = "about:blank") -> ProblemResponse:
    """Build an RFC 7807 problem+json response."""
    body = Problem(type=type_, title=title, status=status, detail=detail)
    return ProblemResponse(status_code=status, content=body.model_dump(exclude_none=True))


class CursorPage(BaseModel, Generic[T]):
    """Cursor-paginated collection envelope.

    ``next_cursor`` is an opaque base64 token; ``null`` means last page.
    """

    items: list[T]
    next_cursor: str | None = None


class PageParams(BaseModel):
    """Standard cursor pagination query parameters."""

    cursor: str | None = None
    limit: int = Field(default=50, ge=1, le=200)


def page_params(
    cursor: Annotated[str | None, Query(description="Opaque cursor from a previous page.")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> PageParams:
    """FastAPI dependency yielding validated pagination parameters."""
    return PageParams(cursor=cursor, limit=limit)


def idempotency_key(
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description="Client-chosen key; repeated POSTs with the same key return the original result.",
        ),
    ] = None,
) -> str | None:
    """FastAPI dependency extracting the Idempotency-Key header on POSTs.

    Services persist (tenant_id, key) -> response for 24h; replays are served
    from that record instead of re-executing the action.
    """
    return idempotency_key
