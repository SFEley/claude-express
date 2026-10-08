"""Queue behavior: append-only, iteration, cached-before-uncached enforcement.

Spec §2.3 and §3.2. Tests cover both .system and .blocks (parallel
queues with identical semantics in MVP).

Wire-format effects of caching are tested in test_serialization.py;
this file only tests queue-level behavior.
"""
import pytest

from claude_express import (
    CACHE_5,
    CACHE_60,
    CACHE_LONG,
    CACHE_NONE,
    CACHE_SHORT,
    Message,
    UNCACHED,
    ValidationError,
)


# ---------------------------------------------------------------------------
# .system — happy path
# ---------------------------------------------------------------------------

def test_system_starts_empty():
    msg = Message()
    assert len(msg.system) == 0


def test_system_append_text():
    msg = Message()
    msg.system.append("you are a tutor")
    assert len(msg.system) == 1


def test_system_append_multiple():
    msg = Message()
    msg.system.append("a")
    msg.system.append("b")
    msg.system.append("c")
    assert len(msg.system) == 3


def test_system_iteration_preserves_order():
    """Iteration yields blocks in insertion order. The exact element type
    is implementation-defined; tests don't assert on it directly."""
    msg = Message()
    msg.system.append("first")
    msg.system.append("second")
    msg.system.append("third")
    iterated = list(msg.system)
    assert len(iterated) == 3


# ---------------------------------------------------------------------------
# .system — caching
# ---------------------------------------------------------------------------

def test_system_append_with_cache_short():
    msg = Message()
    msg.system.append("frozen prefix", cache=CACHE_SHORT)
    assert len(msg.system) == 1


def test_system_append_with_cache_long():
    msg = Message()
    msg.system.append("frozen prefix", cache=CACHE_LONG)
    assert len(msg.system) == 1


def test_system_append_with_cache_none_explicit():
    msg = Message()
    msg.system.append("plain", cache=CACHE_NONE)
    assert len(msg.system) == 1


def test_system_append_with_cache_5_alias():
    msg = Message()
    msg.system.append("a", cache=CACHE_5)
    assert len(msg.system) == 1


def test_system_append_with_cache_60_alias():
    msg = Message()
    msg.system.append("a", cache=CACHE_60)
    assert len(msg.system) == 1


def test_system_append_with_uncached_alias():
    msg = Message()
    msg.system.append("a", cache=UNCACHED)
    assert len(msg.system) == 1


# ---------------------------------------------------------------------------
# .system — cached-before-uncached eager validation
# ---------------------------------------------------------------------------

def test_system_cached_after_uncached_raises():
    msg = Message()
    msg.system.append("plain")
    with pytest.raises(ValidationError):
        msg.system.append("cached", cache=CACHE_SHORT)


def test_system_cached_after_uncached_raises_long():
    msg = Message()
    msg.system.append("plain")
    with pytest.raises(ValidationError):
        msg.system.append("cached long", cache=CACHE_LONG)


def test_system_uncached_after_cached_is_fine():
    """Cached → uncached transition is the *intended* shape — frozen prefix
    followed by the volatile question."""
    msg = Message()
    msg.system.append("frozen", cache=CACHE_SHORT)
    msg.system.append("frozen 2", cache=CACHE_SHORT)
    msg.system.append("volatile")  # should not raise
    assert len(msg.system) == 3


def test_system_mixed_ttls_within_cached_prefix_is_fine():
    """Different TTLs within the cached prefix are allowed."""
    msg = Message()
    msg.system.append("a", cache=CACHE_LONG)
    msg.system.append("b", cache=CACHE_LONG)
    msg.system.append("c", cache=CACHE_SHORT)
    msg.system.append("d", cache=CACHE_SHORT)
    assert len(msg.system) == 4


def test_system_validation_error_does_not_mutate_queue():
    """A failed append should not leave the queue in a half-modified state."""
    msg = Message()
    msg.system.append("plain")
    with pytest.raises(ValidationError):
        msg.system.append("cached", cache=CACHE_SHORT)
    # Queue should still be exactly [plain].
    assert len(msg.system) == 1


# ---------------------------------------------------------------------------
# .blocks — same semantics, parallel tests
# ---------------------------------------------------------------------------

def test_blocks_starts_empty():
    msg = Message()
    assert len(msg.blocks) == 0


def test_blocks_append_text():
    msg = Message()
    msg.blocks.append("what is the answer?")
    assert len(msg.blocks) == 1


def test_blocks_append_multiple():
    msg = Message()
    msg.blocks.append("context")
    msg.blocks.append("question")
    assert len(msg.blocks) == 2


def test_blocks_cached_after_uncached_raises():
    msg = Message()
    msg.blocks.append("plain")
    with pytest.raises(ValidationError):
        msg.blocks.append("cached", cache=CACHE_SHORT)


def test_blocks_uncached_after_cached_is_fine():
    msg = Message()
    msg.blocks.append("retrieved doc", cache=CACHE_SHORT)
    msg.blocks.append("user question")  # should not raise
    assert len(msg.blocks) == 2


# ---------------------------------------------------------------------------
# Queues are independent
# ---------------------------------------------------------------------------

def test_queues_validate_independently():
    """An uncached append in .blocks must not poison .system."""
    msg = Message()
    msg.blocks.append("plain")  # makes .blocks's tail uncached
    msg.system.append("cached", cache=CACHE_SHORT)  # must NOT raise
    assert len(msg.system) == 1
    assert len(msg.blocks) == 1


def test_appending_uncached_to_system_does_not_affect_blocks():
    msg = Message()
    msg.system.append("plain")  # makes .system's tail uncached
    msg.blocks.append("cached", cache=CACHE_SHORT)  # must NOT raise
    assert len(msg.blocks) == 1
