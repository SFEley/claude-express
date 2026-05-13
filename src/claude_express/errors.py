"""Exception hierarchy — see spec §5."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .responses import ErrorResponse


class ExpressError(Exception):
    """Base class for all claude-express errors."""


class ValidationError(ExpressError):
    """Construction-time or append-time validation failure."""


class FrozenMessageError(ExpressError):
    """Mutation or re-send attempted after .send() has populated .response."""


class SerializationError(ExpressError):
    """Wire-format payload cannot be produced (e.g., > 4 cache breakpoints)."""


class DispatchError(ExpressError):
    """Base for send-time failures. Carries the ErrorResponse on .response."""

    def __init__(self, message: str = "", *, response: "ErrorResponse | None" = None) -> None:
        super().__init__(message or (response.message if response else ""))
        self.response: "ErrorResponse | None" = response


class APIError(DispatchError):
    """4xx / 5xx response from Anthropic."""


class ExpressConnectionError(DispatchError):
    """Network / transport-layer failure with no parseable response body."""
