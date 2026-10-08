"""Property getters and setters for Message scalar fields.

Spec §2.1: scalar fields have read/write properties; queue-backed
fields do NOT have a setter. MVP scalars: `model`, `max_tokens`.

Frozen-after-send behavior is NOT tested here — see test_lifecycle.py.
"""
import pytest

from claude_express import Message, ValidationError


# ---------------------------------------------------------------------------
# model
# ---------------------------------------------------------------------------

def test_set_model():
    msg = Message()
    msg.model = "claude-haiku-4-5"
    assert msg.model == "claude-haiku-4-5"


def test_model_set_then_get_round_trip():
    msg = Message(model="claude-opus-4-7")
    msg.model = "claude-sonnet-4-6"
    assert msg.model == "claude-sonnet-4-6"


def test_set_model_to_empty_raises():
    """Same construction-time validation applies to setter."""
    msg = Message()
    with pytest.raises(ValidationError):
        msg.model = ""


# ---------------------------------------------------------------------------
# max_tokens
# ---------------------------------------------------------------------------

def test_set_max_tokens():
    msg = Message()
    msg.max_tokens = 8000
    assert msg.max_tokens == 8000


def test_max_tokens_set_then_get_round_trip():
    msg = Message(max_tokens=4000)
    msg.max_tokens = 12000
    assert msg.max_tokens == 12000


def test_set_max_tokens_zero_raises():
    msg = Message()
    with pytest.raises(ValidationError):
        msg.max_tokens = 0


def test_set_max_tokens_negative_raises():
    msg = Message()
    with pytest.raises(ValidationError):
        msg.max_tokens = -100


# ---------------------------------------------------------------------------
# Queue-backed fields have no setter
# ---------------------------------------------------------------------------

def test_system_setter_does_not_exist():
    """msg.system = '...' should NOT replace the queue.

    Per spec §2.1: queue-backed fields don't have property setters because
    that would violate append-only. The library should raise AttributeError
    or otherwise refuse the assignment.
    """
    msg = Message()
    with pytest.raises((AttributeError, TypeError)):
        msg.system = "hello"


def test_blocks_setter_does_not_exist():
    msg = Message()
    with pytest.raises((AttributeError, TypeError)):
        msg.blocks = "hello"
