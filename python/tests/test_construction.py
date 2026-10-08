"""Message construction — defaults, ergonomic sugar, validation.

Spec §2.2 (constructor) and §3.1 (construction-time validation).
"""
import pytest

from claude_express import Message, ValidationError


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

def test_default_model():
    msg = Message()
    assert msg.model == "claude-opus-4-7"


def test_default_max_tokens():
    msg = Message()
    assert msg.max_tokens == 16000


def test_no_args_constructor_succeeds():
    """Message() with no args is valid; queues are empty."""
    msg = Message()
    assert len(msg.system) == 0
    assert len(msg.blocks) == 0


def test_default_response_is_none():
    """Before .send(), .response is None."""
    msg = Message()
    assert msg.response is None


# ---------------------------------------------------------------------------
# Explicit kwargs (Anthropic-canonical names)
# ---------------------------------------------------------------------------

def test_explicit_model():
    msg = Message(model="claude-haiku-4-5")
    assert msg.model == "claude-haiku-4-5"


def test_explicit_max_tokens():
    msg = Message(max_tokens=8000)
    assert msg.max_tokens == 8000


# ---------------------------------------------------------------------------
# Ergonomic sugar — system= and user=
# ---------------------------------------------------------------------------

def test_user_sugar_appends_to_blocks():
    """Message(user='hi') is sugar for msg.blocks.append('hi')."""
    msg = Message(user="hello")
    assert len(msg.blocks) == 1
    # Equivalence test: a hand-built message produces the same payload
    other = Message()
    other.blocks.append("hello")
    assert msg.payload() == other.payload()


def test_system_sugar_appends_to_system():
    msg = Message(system="you are a helper")
    assert len(msg.system) == 1
    other = Message()
    other.system.append("you are a helper")
    assert msg.payload() == other.payload()


def test_user_and_system_sugar_together():
    msg = Message(system="be concise", user="what is 2+2?")
    assert len(msg.system) == 1
    assert len(msg.blocks) == 1


def test_sugar_values_are_uncached():
    """Sugar always appends uncached. To cache, use queue methods."""
    msg = Message(user="hi", system="you are X")
    payload = msg.payload()
    # Neither block should carry a cache_control marker.
    assert "cache_control" not in payload["system"][0]
    assert "cache_control" not in payload["messages"][0]["content"][0]


# ---------------------------------------------------------------------------
# Construction-time validation
# ---------------------------------------------------------------------------

def test_zero_max_tokens_raises():
    with pytest.raises(ValidationError):
        Message(max_tokens=0)


def test_negative_max_tokens_raises():
    with pytest.raises(ValidationError):
        Message(max_tokens=-1)


def test_empty_model_raises():
    with pytest.raises(ValidationError):
        Message(model="")


def test_unknown_model_string_does_not_raise():
    """Express does not maintain a model allowlist — Anthropic rejects unknowns at send time."""
    msg = Message(model="some-future-model-name")
    assert msg.model == "some-future-model-name"
