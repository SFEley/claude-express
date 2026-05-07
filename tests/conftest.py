"""Shared test fixtures.

The StubDispatcher implements the minimal Dispatcher protocol described
in spec §7: a class with an async `send(message) -> Response | ErrorResponse`.
Tests configure what it returns (or what exception it raises before returning)
and inspect what it was called with.

Tests do NOT touch the real Dispatcher class — that's a separate brainstorm.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from claude_express import ErrorResponse, Message, Response


class StubDispatcher:
    """In-process dispatcher stub for Message tests.

    Configure with one of:
        - returns=<Response or ErrorResponse>: what `send()` returns
        - raises=<Exception>: what `send()` raises before returning anything

    Inspect after the test:
        - .calls: list of Message instances passed to send(), in order
    """

    def __init__(
        self,
        *,
        returns: "Response | ErrorResponse | None" = None,
        raises: BaseException | None = None,
    ) -> None:
        self.returns = returns
        self.raises = raises
        self.calls: list["Message"] = []

    async def send(self, message: "Message") -> "Response | ErrorResponse":
        self.calls.append(message)
        if self.raises is not None:
            raise self.raises
        if self.returns is None:
            raise RuntimeError(
                "StubDispatcher.send() called but `returns` was not configured "
                "and `raises` was not set. Configure the stub before calling .send()."
            )
        return self.returns


@pytest.fixture
def stub_dispatcher() -> StubDispatcher:
    """Fresh StubDispatcher per test, unconfigured by default."""
    return StubDispatcher()


@pytest.fixture
def sample_success_raw() -> dict:
    """A minimal successful API response body."""
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-4-7",
        "content": [{"type": "text", "text": "ok"}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": 1,
            "output_tokens": 1,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
        },
    }


@pytest.fixture
def sample_error_raw() -> dict:
    """A minimal error API response body."""
    return {
        "type": "error",
        "error": {
            "type": "invalid_request_error",
            "message": "bad request",
        },
        "request_id": "req_test",
    }
