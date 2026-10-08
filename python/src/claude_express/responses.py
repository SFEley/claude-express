"""Response and ErrorResponse — see spec §4.2 and §4.3."""
from __future__ import annotations


class _Usage:
    """Token-usage subobject of a successful Response."""

    __slots__ = (
        "input_tokens",
        "output_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
    )

    def __init__(self, raw: dict) -> None:
        self.input_tokens = raw.get("input_tokens", 0)
        self.output_tokens = raw.get("output_tokens", 0)
        self.cache_read_input_tokens = raw.get("cache_read_input_tokens", 0)
        self.cache_creation_input_tokens = raw.get("cache_creation_input_tokens", 0)


class Response:
    """Successful /v1/messages response."""

    is_error = False

    def __init__(self, *, raw: dict) -> None:
        self.raw = raw
        self.usage = _Usage(raw.get("usage", {}))

    @property
    def text(self) -> str:
        """Concatenation of every text-typed block in content."""
        parts = [
            block.get("text", "")
            for block in self.raw.get("content", [])
            if block.get("type") == "text"
        ]
        return "".join(parts)

    @property
    def stop_reason(self) -> str | None:
        return self.raw.get("stop_reason")


class ErrorResponse:
    """Failure response — API error or transport-layer error.

    status_code=0 conventionally signals a transport-layer failure with
    no parseable body; raw will be None in that case.
    """

    is_error = True

    def __init__(
        self,
        *,
        status_code: int,
        error_type: str,
        message: str,
        request_id: str | None,
        raw: dict | None,
    ) -> None:
        self.status_code = status_code
        self.error_type = error_type
        self.message = message
        self.request_id = request_id
        self.raw = raw
