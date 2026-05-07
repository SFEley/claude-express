"""Frozen-after-send invariant.

Spec §4.4: once .response is populated (success or error), all
mutation raises FrozenMessageError, and a second .send() also raises.
There is no fork/copy primitive in MVP.
"""
import pytest

from claude_express import (
    CACHE_SHORT,
    ErrorResponse,
    FrozenMessageError,
    Message,
    Response,
)
from tests.conftest import StubDispatcher


def make_success() -> Response:
    return Response(raw={
        "content": [{"type": "text", "text": "ok"}],
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 1,
            "output_tokens": 1,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
        },
    })


def make_api_error() -> ErrorResponse:
    return ErrorResponse(
        status_code=400,
        error_type="invalid_request_error",
        message="bad",
        request_id="req_x",
        raw={},
    )


# ---------------------------------------------------------------------------
# Frozen after successful send
# ---------------------------------------------------------------------------

async def test_queue_append_after_send_success_raises():
    stub = StubDispatcher(returns=make_success())
    msg = Message(dispatcher=stub)
    msg.system.append("a")
    msg.blocks.append("hi")
    await msg.send()
    with pytest.raises(FrozenMessageError):
        msg.system.append("b")


async def test_blocks_append_after_send_success_raises():
    stub = StubDispatcher(returns=make_success())
    msg = Message(dispatcher=stub)
    msg.blocks.append("hi")
    await msg.send()
    with pytest.raises(FrozenMessageError):
        msg.blocks.append("more")


async def test_queue_append_with_cache_after_send_success_raises():
    """The frozen check fires regardless of the cache argument."""
    stub = StubDispatcher(returns=make_success())
    msg = Message(dispatcher=stub)
    msg.blocks.append("hi")
    await msg.send()
    with pytest.raises(FrozenMessageError):
        msg.system.append("cached", cache=CACHE_SHORT)


async def test_set_model_after_send_success_raises():
    stub = StubDispatcher(returns=make_success())
    msg = Message(dispatcher=stub)
    msg.blocks.append("hi")
    await msg.send()
    with pytest.raises(FrozenMessageError):
        msg.model = "claude-haiku-4-5"


async def test_set_max_tokens_after_send_success_raises():
    stub = StubDispatcher(returns=make_success())
    msg = Message(dispatcher=stub)
    msg.blocks.append("hi")
    await msg.send()
    with pytest.raises(FrozenMessageError):
        msg.max_tokens = 8000


async def test_second_send_after_success_raises():
    stub = StubDispatcher(returns=make_success())
    msg = Message(dispatcher=stub)
    msg.blocks.append("hi")
    await msg.send()
    with pytest.raises(FrozenMessageError):
        await msg.send()


# ---------------------------------------------------------------------------
# Frozen after failed send (with raise_on_failure=False, so we can keep
# the message reference around without dealing with a propagated exception)
# ---------------------------------------------------------------------------

async def test_queue_append_after_send_failure_raises():
    """A failed send freezes the message just as a successful one does."""
    stub = StubDispatcher(returns=make_api_error())
    msg = Message(dispatcher=stub, raise_on_failure=False)
    msg.blocks.append("hi")
    await msg.send()
    assert msg.response is not None
    assert msg.response.is_error is True
    with pytest.raises(FrozenMessageError):
        msg.blocks.append("retry")


async def test_set_model_after_send_failure_raises():
    stub = StubDispatcher(returns=make_api_error())
    msg = Message(dispatcher=stub, raise_on_failure=False)
    msg.blocks.append("hi")
    await msg.send()
    with pytest.raises(FrozenMessageError):
        msg.model = "different"


async def test_second_send_after_failure_raises():
    """No retry-via-resend in MVP."""
    stub = StubDispatcher(returns=make_api_error())
    msg = Message(dispatcher=stub, raise_on_failure=False)
    msg.blocks.append("hi")
    await msg.send()
    with pytest.raises(FrozenMessageError):
        await msg.send()


# ---------------------------------------------------------------------------
# Frozen also after a send that raised (raise_on_failure=True path)
# ---------------------------------------------------------------------------

async def test_freeze_persists_through_propagated_exception():
    """When .send() raises (raise_on_failure=True default), the message
    is still frozen — the freeze happens before the raise."""
    from claude_express import DispatchError

    stub = StubDispatcher(returns=make_api_error())
    msg = Message(dispatcher=stub)  # default raise_on_failure=True
    msg.blocks.append("hi")
    try:
        await msg.send()
    except DispatchError:
        pass

    # Frozen.
    with pytest.raises(FrozenMessageError):
        msg.blocks.append("retry")
    with pytest.raises(FrozenMessageError):
        msg.model = "x"
