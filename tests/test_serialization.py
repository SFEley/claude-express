"""Wire serialization via Message.payload().

Spec §3.3, §6.

The payload() method returns a dict matching Anthropic's /v1/messages
request body. Tests assert exact dict shape against fixed inputs.

Cache marker placement uses run-collapsing: walk each queue, group
contiguous same-TTL cached blocks, place ONE cache_control marker on
the LAST block of each group. Total markers across all queues ≤ 4
(Anthropic's limit) — exceeding raises SerializationError.

Wire formats (from spec §2.3 and Anthropic's API):
- 5-min TTL: cache_control = {"type": "ephemeral"}  (no `ttl` field)
- 1-hour TTL: cache_control = {"type": "ephemeral", "ttl": "1h"}
"""
import pytest

from claude_express import (
    CACHE_LONG,
    CACHE_SHORT,
    Message,
    SerializationError,
)


# ---------------------------------------------------------------------------
# Basic payload structure
# ---------------------------------------------------------------------------

def test_payload_includes_model_and_max_tokens():
    msg = Message(model="claude-opus-4-7", max_tokens=8000)
    msg.blocks.append("hi")
    payload = msg.payload()
    assert payload["model"] == "claude-opus-4-7"
    assert payload["max_tokens"] == 8000


def test_payload_user_message_structure():
    """A single user-content block produces a single user message with
    one text content block."""
    msg = Message()
    msg.blocks.append("hello")
    payload = msg.payload()
    assert payload["messages"] == [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "hello"},
            ],
        },
    ]


def test_payload_multiple_user_blocks_in_one_message():
    """Multiple appends to .blocks produce multiple content blocks within
    a SINGLE user message (single user turn — multi-turn deferred)."""
    msg = Message()
    msg.blocks.append("part 1")
    msg.blocks.append("part 2")
    payload = msg.payload()
    assert len(payload["messages"]) == 1
    assert payload["messages"][0]["role"] == "user"
    assert len(payload["messages"][0]["content"]) == 2


def test_payload_omits_system_when_empty():
    """Spec §6.3: empty .system queue → no `system` key in payload."""
    msg = Message()
    msg.blocks.append("hi")
    payload = msg.payload()
    assert "system" not in payload


def test_payload_messages_empty_list_when_blocks_empty():
    """Spec §6.3: empty .blocks queue → messages is []. Anthropic
    will reject; that surfaces as APIError, not pre-validation."""
    msg = Message()
    payload = msg.payload()
    assert payload["messages"] == []


def test_payload_includes_system_array_form():
    msg = Message()
    msg.system.append("you are a tutor")
    msg.blocks.append("hello")
    payload = msg.payload()
    assert payload["system"] == [
        {"type": "text", "text": "you are a tutor"},
    ]


# ---------------------------------------------------------------------------
# Render order — tools → system → messages
# ---------------------------------------------------------------------------

def test_payload_render_order_keys():
    """Tools deferred in MVP, so order is system → messages. Keys may
    appear in any order in a dict, but we test that the values are
    structured to imply Anthropic's render order at serialization."""
    msg = Message()
    msg.system.append("sys")
    msg.blocks.append("user msg")
    payload = msg.payload()
    assert "system" in payload
    assert "messages" in payload


def test_append_order_does_not_affect_payload_layout():
    """Appending to .blocks before .system still produces the same payload."""
    msg_a = Message()
    msg_a.system.append("sys")
    msg_a.blocks.append("user msg")

    msg_b = Message()
    msg_b.blocks.append("user msg")
    msg_b.system.append("sys")

    assert msg_a.payload() == msg_b.payload()


# ---------------------------------------------------------------------------
# Wire format for cache markers
# ---------------------------------------------------------------------------

def test_cache_short_wire_format():
    """5-min TTL → no `ttl` field (Anthropic's default)."""
    msg = Message()
    msg.system.append("a", cache=CACHE_SHORT)
    payload = msg.payload()
    assert payload["system"][0] == {
        "type": "text",
        "text": "a",
        "cache_control": {"type": "ephemeral"},
    }


def test_cache_long_wire_format():
    """1-hour TTL → `ttl: "1h"`."""
    msg = Message()
    msg.system.append("a", cache=CACHE_LONG)
    payload = msg.payload()
    assert payload["system"][0] == {
        "type": "text",
        "text": "a",
        "cache_control": {"type": "ephemeral", "ttl": "1h"},
    }


def test_uncached_block_has_no_cache_control():
    msg = Message()
    msg.system.append("a")
    payload = msg.payload()
    assert payload["system"][0] == {"type": "text", "text": "a"}
    assert "cache_control" not in payload["system"][0]


# ---------------------------------------------------------------------------
# Run-collapsed marker placement
# ---------------------------------------------------------------------------

def test_run_collapse_single_short_block():
    """One cached block → marker on that block."""
    msg = Message()
    msg.system.append("only", cache=CACHE_SHORT)
    payload = msg.payload()
    assert payload["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_run_collapse_two_same_ttl_marker_on_last():
    """Two consecutive same-TTL cached blocks → marker only on the second."""
    msg = Message()
    msg.system.append("a", cache=CACHE_SHORT)
    msg.system.append("b", cache=CACHE_SHORT)
    payload = msg.payload()
    assert "cache_control" not in payload["system"][0]
    assert payload["system"][1]["cache_control"] == {"type": "ephemeral"}


def test_run_collapse_three_same_ttl_marker_on_last():
    msg = Message()
    msg.system.append("a", cache=CACHE_LONG)
    msg.system.append("b", cache=CACHE_LONG)
    msg.system.append("c", cache=CACHE_LONG)
    payload = msg.payload()
    assert "cache_control" not in payload["system"][0]
    assert "cache_control" not in payload["system"][1]
    assert payload["system"][2]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}


def test_run_collapse_ttl_transition_creates_new_group():
    """CACHE_LONG run then CACHE_SHORT run → marker at end of each."""
    msg = Message()
    msg.system.append("frozen 1", cache=CACHE_LONG)
    msg.system.append("frozen 2", cache=CACHE_LONG)
    msg.system.append("session 1", cache=CACHE_SHORT)
    msg.system.append("session 2", cache=CACHE_SHORT)
    payload = msg.payload()

    assert "cache_control" not in payload["system"][0]
    assert payload["system"][1]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert "cache_control" not in payload["system"][2]
    assert payload["system"][3]["cache_control"] == {"type": "ephemeral"}


def test_run_collapse_cached_to_uncached_transition_marks_last_cached():
    """Trailing uncached blocks get no marker; the last cached block gets one."""
    msg = Message()
    msg.system.append("a", cache=CACHE_SHORT)
    msg.system.append("b", cache=CACHE_SHORT)
    msg.system.append("c")
    msg.system.append("d")
    payload = msg.payload()

    assert "cache_control" not in payload["system"][0]
    assert payload["system"][1]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in payload["system"][2]
    assert "cache_control" not in payload["system"][3]


def test_run_collapse_independent_per_queue():
    """Run-collapsing happens within a queue, not across queues."""
    msg = Message()
    msg.system.append("sys cached", cache=CACHE_SHORT)
    msg.blocks.append("blocks cached", cache=CACHE_SHORT)
    payload = msg.payload()

    # Each queue gets its own marker.
    assert payload["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert payload["messages"][0]["content"][0]["cache_control"] == {"type": "ephemeral"}


# ---------------------------------------------------------------------------
# 4-breakpoint global limit
# ---------------------------------------------------------------------------

def test_payload_with_four_breakpoints_succeeds():
    """Exactly 4 markers across queues — at the limit, must succeed."""
    msg = Message()
    # Two cached groups in .system (CACHE_LONG run, then CACHE_SHORT run)
    msg.system.append("a", cache=CACHE_LONG)
    msg.system.append("b", cache=CACHE_SHORT)
    # Two cached groups in .blocks
    msg.blocks.append("c", cache=CACHE_LONG)
    msg.blocks.append("d", cache=CACHE_SHORT)
    msg.blocks.append("e")  # uncached question

    payload = msg.payload()
    # Should not raise. Verify shape.
    assert payload["system"][0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert payload["system"][1]["cache_control"] == {"type": "ephemeral"}
    assert payload["messages"][0]["content"][0]["cache_control"] == {
        "type": "ephemeral", "ttl": "1h",
    }
    assert payload["messages"][0]["content"][1]["cache_control"] == {"type": "ephemeral"}


def test_payload_with_five_breakpoints_raises():
    """5 markers > Anthropic's 4-breakpoint limit → SerializationError."""
    msg = Message()
    # Three cached groups in .system: alternating TTLs to force three markers
    msg.system.append("a", cache=CACHE_LONG)
    msg.system.append("b", cache=CACHE_SHORT)
    msg.system.append("c", cache=CACHE_LONG)
    # Two cached groups in .blocks
    msg.blocks.append("d", cache=CACHE_LONG)
    msg.blocks.append("e", cache=CACHE_SHORT)
    msg.blocks.append("f")

    with pytest.raises(SerializationError):
        msg.payload()


# ---------------------------------------------------------------------------
# Worked example from spec §6.1
# ---------------------------------------------------------------------------

def test_spec_section_6_1_worked_example():
    """Exact reproduction of the worked example in spec §6.1."""
    msg = Message(model="claude-opus-4-7", max_tokens=16000)
    msg.system.append("You are a tutor.", cache=CACHE_LONG)
    msg.system.append("Always cite sources.", cache=CACHE_LONG)
    msg.system.append("Today's session is about geometry.", cache=CACHE_SHORT)
    msg.blocks.append("What is the area of a triangle?")

    assert msg.payload() == {
        "model": "claude-opus-4-7",
        "max_tokens": 16000,
        "system": [
            {"type": "text", "text": "You are a tutor."},
            {
                "type": "text",
                "text": "Always cite sources.",
                "cache_control": {"type": "ephemeral", "ttl": "1h"},
            },
            {
                "type": "text",
                "text": "Today's session is about geometry.",
                "cache_control": {"type": "ephemeral"},
            },
        ],
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is the area of a triangle?"},
                ],
            },
        ],
    }
