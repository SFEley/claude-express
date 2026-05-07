"""Message.send() — dispatcher resolution, success path, failure handling.

Spec §4.1, §4.2, §4.3, §5.

Uses the StubDispatcher from conftest.py. Tests do not touch real
networking or the real Dispatcher class.

Frozen-after-send invariant is tested in test_lifecycle.py — only
the immediate return / raise behavior is tested here.
"""
import pytest

import claude_express as express
from claude_express import (
    APIError,
    DispatchError,
    ErrorResponse,
    ExpressConnectionError,
    Message,
    Response,
)
from tests.conftest import StubDispatcher


# Reusable canned responses
def make_success(usage: dict | None = None) -> Response:
    return Response(raw={
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-4-7",
        "content": [{"type": "text", "text": "ok"}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": usage or {
            "input_tokens": 1,
            "output_tokens": 1,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
        },
    })


def make_api_error(status: int = 400) -> ErrorResponse:
    return ErrorResponse(
        status_code=status,
        error_type="invalid_request_error",
        message="bad request",
        request_id="req_test",
        raw={
            "type": "error",
            "error": {"type": "invalid_request_error", "message": "bad request"},
            "request_id": "req_test",
        },
    )


def make_connection_error() -> ErrorResponse:
    return ErrorResponse(
        status_code=0,
        error_type="connection_error",
        message="connection refused",
        request_id=None,
        raw=None,
    )


# ---------------------------------------------------------------------------
# Dispatcher resolution
# ---------------------------------------------------------------------------

async def test_send_uses_constructor_injected_dispatcher(stub_dispatcher):
    stub_dispatcher.returns = make_success()
    msg = Message(dispatcher=stub_dispatcher)
    msg.blocks.append("hi")
    await msg.send()
    assert stub_dispatcher.calls == [msg]


async def test_send_falls_back_to_module_default(monkeypatch, stub_dispatcher):
    """When dispatcher=None on construction, .send() looks up express.dispatcher."""
    stub_dispatcher.returns = make_success()
    monkeypatch.setattr(express, "dispatcher", stub_dispatcher, raising=False)
    msg = Message()  # no dispatcher injected
    msg.blocks.append("hi")
    await msg.send()
    assert stub_dispatcher.calls == [msg]


async def test_constructor_dispatcher_overrides_module_default(monkeypatch):
    """If both are present, the constructor-injected one wins."""
    default = StubDispatcher(returns=make_success())
    injected = StubDispatcher(returns=make_success())
    monkeypatch.setattr(express, "dispatcher", default, raising=False)
    msg = Message(dispatcher=injected)
    msg.blocks.append("hi")
    await msg.send()
    assert injected.calls == [msg]
    assert default.calls == []


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------

async def test_send_success_sets_response(stub_dispatcher):
    canned = make_success()
    stub_dispatcher.returns = canned
    msg = Message(dispatcher=stub_dispatcher)
    msg.blocks.append("hi")
    await msg.send()
    assert msg.response is canned


async def test_send_success_returns_response(stub_dispatcher):
    canned = make_success()
    stub_dispatcher.returns = canned
    msg = Message(dispatcher=stub_dispatcher)
    msg.blocks.append("hi")
    result = await msg.send()
    assert result is canned


async def test_send_success_response_is_not_error(stub_dispatcher):
    stub_dispatcher.returns = make_success()
    msg = Message(dispatcher=stub_dispatcher)
    msg.blocks.append("hi")
    await msg.send()
    assert msg.response.is_error is False


# ---------------------------------------------------------------------------
# Failure with raise_on_failure=True (default)
# ---------------------------------------------------------------------------

async def test_send_failure_default_raises(stub_dispatcher):
    """Default raise_on_failure=True; an ErrorResponse return raises."""
    stub_dispatcher.returns = make_api_error(400)
    msg = Message(dispatcher=stub_dispatcher)
    msg.blocks.append("hi")
    with pytest.raises(DispatchError):
        await msg.send()


async def test_send_failure_default_raises_api_error_subclass(stub_dispatcher):
    """4xx/5xx errors raise APIError specifically."""
    stub_dispatcher.returns = make_api_error(429)
    msg = Message(dispatcher=stub_dispatcher)
    msg.blocks.append("hi")
    with pytest.raises(APIError):
        await msg.send()


async def test_send_failure_default_raises_connection_error_subclass(stub_dispatcher):
    """status_code=0 transport errors raise ExpressConnectionError specifically."""
    stub_dispatcher.returns = make_connection_error()
    msg = Message(dispatcher=stub_dispatcher)
    msg.blocks.append("hi")
    with pytest.raises(ExpressConnectionError):
        await msg.send()


async def test_send_failure_attaches_response_even_when_raising(stub_dispatcher):
    """Spec §4.4: .response is set BEFORE the exception propagates,
    so post-mortem inspection works after try/except."""
    stub_dispatcher.returns = make_api_error(500)
    msg = Message(dispatcher=stub_dispatcher)
    msg.blocks.append("hi")
    try:
        await msg.send()
    except DispatchError:
        pass
    assert msg.response is not None
    assert msg.response.is_error is True
    assert msg.response.status_code == 500


async def test_send_failure_exception_carries_response(stub_dispatcher):
    """The raised exception has a .response attribute carrying the same
    ErrorResponse — convenient when the caller doesn't have the message
    in scope, only the exception."""
    canned_error = make_api_error(400)
    stub_dispatcher.returns = canned_error
    msg = Message(dispatcher=stub_dispatcher)
    msg.blocks.append("hi")
    with pytest.raises(DispatchError) as exc_info:
        await msg.send()
    assert exc_info.value.response is canned_error


# ---------------------------------------------------------------------------
# Failure with raise_on_failure=False (constructor)
# ---------------------------------------------------------------------------

async def test_send_failure_constructor_suppress_does_not_raise(stub_dispatcher):
    stub_dispatcher.returns = make_api_error(400)
    msg = Message(dispatcher=stub_dispatcher, raise_on_failure=False)
    msg.blocks.append("hi")
    # Should NOT raise — return the error.
    result = await msg.send()
    assert result.is_error is True
    assert msg.response is result


async def test_send_failure_constructor_suppress_attaches_error(stub_dispatcher):
    canned = make_api_error(429)
    stub_dispatcher.returns = canned
    msg = Message(dispatcher=stub_dispatcher, raise_on_failure=False)
    msg.blocks.append("hi")
    await msg.send()
    assert msg.response is canned


# ---------------------------------------------------------------------------
# Failure with raise_on_failure=False (per-call)
# ---------------------------------------------------------------------------

async def test_send_failure_per_call_suppress(stub_dispatcher):
    """Per-call kwarg overrides constructor default."""
    stub_dispatcher.returns = make_api_error(500)
    msg = Message(dispatcher=stub_dispatcher)  # default raise_on_failure=True
    msg.blocks.append("hi")
    result = await msg.send(raise_on_failure=False)  # override per-call
    assert result.is_error is True
    assert msg.response is result


async def test_send_per_call_can_re_enable_raising(stub_dispatcher):
    """Per-call True overrides constructor False."""
    stub_dispatcher.returns = make_api_error(400)
    msg = Message(dispatcher=stub_dispatcher, raise_on_failure=False)
    msg.blocks.append("hi")
    with pytest.raises(DispatchError):
        await msg.send(raise_on_failure=True)
