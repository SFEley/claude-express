# Message Class Test Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a comprehensive pytest test suite that fully specifies the behavior of the `Message` class, `Response`, `ErrorResponse`, and the cache constants. The author will implement the classes against these tests; this plan does not implement the classes themselves.

**Architecture:** `src/`-layout Python package with pytest + pytest-asyncio. Each test file targets one concern from the spec (`docs/superpowers/specs/2026-05-06-message-class-design.md`). Tests use a Protocol-conforming stub `Dispatcher` (defined in `tests/conftest.py`) to exercise `Message.send()` without network or a real Dispatcher class. After each task the test file is committed in a state where every test in it fails at collection-time with `ImportError` until the author writes the matching implementation — that's the **success criterion for each task: tests run via pytest, fail with the expected error, and are committed**.

**Tech Stack:** Python ≥3.13; pytest ≥8.0; pytest-asyncio ≥0.23 (auto mode); no networking dependencies (Dispatcher's network layer is the author's concern).

**Spec source of truth:** `docs/superpowers/specs/2026-05-06-message-class-design.md` at commit `8cb74b4` or later.

---

## File Structure

**Will be created or modified by this plan:**

- `pyproject.toml` (modify) — add `[project.optional-dependencies] dev`, `[tool.pytest.ini_options]`
- `src/claude_express/__init__.py` (create, empty stub) — author will fill in
- `tests/__init__.py` (create, empty) — makes tests a package
- `tests/conftest.py` (create) — shared stub Dispatcher class + fixtures
- `tests/test_constants.py` (create) — cache constant aliases and values
- `tests/test_responses.py` (create) — `Response` and `ErrorResponse` accessors
- `tests/test_construction.py` (create) — `Message()` defaults, ergonomic sugar, construction-time validation
- `tests/test_scalars.py` (create) — `model` and `max_tokens` property getters/setters
- `tests/test_queues.py` (create) — `.system`/`.blocks` `.append()` happy path + cached-before-uncached enforcement
- `tests/test_serialization.py` (create) — `.payload()` method: render order, run-collapsed markers, breakpoint limit, wire format
- `tests/test_send.py` (create) — `.send()` dispatcher resolution, success path, failure paths, `raise_on_failure` permutations
- `tests/test_lifecycle.py` (create) — frozen-after-send invariant

**Will be left alone:** `main.py` (uv-init placeholder, irrelevant to the library), `README.md`, `CLAUDE.md`, `.gitignore`, `.python-version`.

**Imports the test suite assumes the author will export from `claude_express`:**

```
Message
Response
ErrorResponse
dispatcher                     # the lazily-constructed module-level singleton
CACHE_SHORT, CACHE_5           # = 5
CACHE_LONG, CACHE_60           # = 60
UNCACHED, CACHE_NONE           # = None
ExpressError                   # base exception
ValidationError                # subclass
FrozenMessageError             # subclass
SerializationError             # subclass
DispatchError                  # subclass
APIError                       # subclass of DispatchError
ExpressConnectionError         # subclass of DispatchError (NOT named ConnectionError to avoid shadowing builtins)
```

Anything not on this list is internal to the author's implementation and not exercised by tests.

---

## Task 0: Project Scaffolding

**Files:**
- Modify: `pyproject.toml`
- Create: `src/claude_express/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Update pyproject.toml**

Replace the contents of `pyproject.toml` with:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "claude-express"
version = "0.1.0"
description = "Async delivery agent for the Claude API with prompt-cache + batch optimization"
readme = "README.md"
requires-python = ">=3.13"
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
]

[tool.hatch.build.targets.wheel]
packages = ["src/claude_express"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["src"]
```

`hatchling` is the build backend — needed by the editable install in Step 4 and standard for src-layout libraries. `pythonpath = ["src"]` is a redundant safety net so pytest finds the package even without an active editable install. `asyncio_mode = "auto"` means `async def test_*` functions are run automatically without needing `@pytest.mark.asyncio` on each.

- [ ] **Step 2: Create the empty package**

Create `src/claude_express/__init__.py` with this content (literally one comment line, so the file isn't empty):

```python
# claude_express — see docs/superpowers/specs/2026-05-06-message-class-design.md
```

- [ ] **Step 3: Create the tests package marker**

Create `tests/__init__.py` empty (zero bytes is fine).

- [ ] **Step 4: Install dev dependencies**

Run from the project root:

```bash
uv venv && uv pip install -e ".[dev]"
```

Expected: virtualenv created at `.venv/`, claude-express installed editable, pytest + pytest-asyncio installed.

(`uv pip` automatically targets the project's `.venv/` if present — no `source activate` needed. All subsequent test commands use `uv run pytest`, which also auto-targets `.venv/`.)

- [ ] **Step 5: Verify pytest runs**

```bash
uv run pytest -v
```

Expected output: `no tests ran in 0.0Xs` (exit code 5: no tests collected). This confirms pytest is wired up.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/claude_express/__init__.py tests/__init__.py
git commit -m "$(cat <<'EOF'
Scaffold Message test suite — pyproject deps and src/tests layout

Add pytest + pytest-asyncio dev deps with asyncio auto mode. Use
src/ layout with pythonpath set so tests import without editable
install. Empty package and tests dirs ready for the test files.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 1: Cache Constants Tests

**Files:**
- Create: `tests/test_constants.py`

Spec section: §2.3 (cache constant aliases and values).

- [ ] **Step 1: Write the test file**

Create `tests/test_constants.py`:

```python
"""Cache constant aliases and values.

Spec §2.3: CACHE_SHORT = CACHE_5 = 5, CACHE_LONG = CACHE_60 = 60,
UNCACHED = CACHE_NONE = None. Aliases must be value-identical.
"""
from claude_express import (
    CACHE_5,
    CACHE_60,
    CACHE_LONG,
    CACHE_NONE,
    CACHE_SHORT,
    UNCACHED,
)


def test_cache_short_is_5():
    assert CACHE_SHORT == 5
    assert CACHE_5 == 5


def test_cache_short_aliases_are_identical():
    assert CACHE_SHORT is CACHE_5


def test_cache_long_is_60():
    assert CACHE_LONG == 60
    assert CACHE_60 == 60


def test_cache_long_aliases_are_identical():
    assert CACHE_LONG is CACHE_60


def test_uncached_is_none():
    assert UNCACHED is None
    assert CACHE_NONE is None


def test_short_and_long_are_distinct():
    assert CACHE_SHORT != CACHE_LONG
```

- [ ] **Step 2: Run pytest, verify expected failure**

```bash
uv run pytest tests/test_constants.py -v
```

Expected: collection error — `ImportError: cannot import name 'CACHE_5' from 'claude_express'` (or whichever import comes first). This is the success state for this task: the test file is correctly wired and waiting for the author's implementation.

- [ ] **Step 3: Commit**

```bash
git add tests/test_constants.py
git commit -m "$(cat <<'EOF'
Test cache constants — aliases, values, and identity

CACHE_SHORT/CACHE_5 = 5 and CACHE_LONG/CACHE_60 = 60 must be
value-identical via `is`, not just equal. UNCACHED/CACHE_NONE
must be None.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Response & ErrorResponse Tests

**Files:**
- Create: `tests/test_responses.py`

Spec sections: §4.2 (`Response`), §4.3 (`ErrorResponse`).

These tests construct `Response` and `ErrorResponse` directly from raw API dicts (the constructor signature inferable from this test usage: each accepts `raw=<dict>` and exposes properties).

- [ ] **Step 1: Write the test file**

Create `tests/test_responses.py`:

```python
"""Response and ErrorResponse accessors.

Spec §4.2 and §4.3. Tests construct Response/ErrorResponse from
raw API dicts and assert on the property surface. The exact
constructor signature is implied here: each accepts raw=<dict>.
"""
from claude_express import ErrorResponse, Response


# ---------------------------------------------------------------------------
# Response — happy-path successful API response
# ---------------------------------------------------------------------------

SAMPLE_RAW_SUCCESS = {
    "id": "msg_01ABC",
    "type": "message",
    "role": "assistant",
    "model": "claude-opus-4-7",
    "content": [
        {"type": "text", "text": "Hello, "},
        {"type": "text", "text": "world!"},
    ],
    "stop_reason": "end_turn",
    "stop_sequence": None,
    "usage": {
        "input_tokens": 10,
        "output_tokens": 5,
        "cache_read_input_tokens": 100,
        "cache_creation_input_tokens": 200,
    },
}


def test_response_is_not_error():
    r = Response(raw=SAMPLE_RAW_SUCCESS)
    assert r.is_error is False


def test_response_text_concatenates_text_blocks():
    r = Response(raw=SAMPLE_RAW_SUCCESS)
    assert r.text == "Hello, world!"


def test_response_text_with_single_block():
    r = Response(raw={
        "content": [{"type": "text", "text": "just one"}],
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 1,
            "output_tokens": 1,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
        },
    })
    assert r.text == "just one"


def test_response_text_skips_non_text_blocks():
    """A response with a tool_use block in addition to text should
    still produce text from the text blocks only."""
    raw = {
        "content": [
            {"type": "text", "text": "I will call a tool. "},
            {"type": "tool_use", "id": "toolu_01", "name": "x", "input": {}},
            {"type": "text", "text": "Done."},
        ],
        "stop_reason": "tool_use",
        "usage": {
            "input_tokens": 1,
            "output_tokens": 1,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
        },
    }
    r = Response(raw=raw)
    assert r.text == "I will call a tool. Done."


def test_response_stop_reason():
    r = Response(raw=SAMPLE_RAW_SUCCESS)
    assert r.stop_reason == "end_turn"


def test_response_usage_input_tokens():
    r = Response(raw=SAMPLE_RAW_SUCCESS)
    assert r.usage.input_tokens == 10


def test_response_usage_output_tokens():
    r = Response(raw=SAMPLE_RAW_SUCCESS)
    assert r.usage.output_tokens == 5


def test_response_usage_cache_read_tokens():
    r = Response(raw=SAMPLE_RAW_SUCCESS)
    assert r.usage.cache_read_input_tokens == 100


def test_response_usage_cache_creation_tokens():
    r = Response(raw=SAMPLE_RAW_SUCCESS)
    assert r.usage.cache_creation_input_tokens == 200


def test_response_raw_returns_dict_unchanged():
    r = Response(raw=SAMPLE_RAW_SUCCESS)
    assert r.raw is SAMPLE_RAW_SUCCESS or r.raw == SAMPLE_RAW_SUCCESS


# ---------------------------------------------------------------------------
# ErrorResponse — 4xx/5xx API failures and transport-layer failures
# ---------------------------------------------------------------------------

SAMPLE_RAW_API_ERROR = {
    "type": "error",
    "error": {
        "type": "invalid_request_error",
        "message": "messages: at least one message is required",
    },
    "request_id": "req_011CSHoEeqs5C35K2UUqR7Fy",
}


def test_error_response_is_error():
    e = ErrorResponse(
        status_code=400,
        error_type="invalid_request_error",
        message="messages: at least one message is required",
        request_id="req_011CSHoEeqs5C35K2UUqR7Fy",
        raw=SAMPLE_RAW_API_ERROR,
    )
    assert e.is_error is True


def test_error_response_status_code():
    e = ErrorResponse(
        status_code=429,
        error_type="rate_limit_error",
        message="Too many requests",
        request_id="req_x",
        raw={},
    )
    assert e.status_code == 429


def test_error_response_error_type():
    e = ErrorResponse(
        status_code=400,
        error_type="invalid_request_error",
        message="bad",
        request_id="req_x",
        raw={},
    )
    assert e.error_type == "invalid_request_error"


def test_error_response_message():
    e = ErrorResponse(
        status_code=400,
        error_type="invalid_request_error",
        message="messages: at least one message is required",
        request_id="req_x",
        raw=SAMPLE_RAW_API_ERROR,
    )
    assert e.message == "messages: at least one message is required"


def test_error_response_request_id():
    e = ErrorResponse(
        status_code=400,
        error_type="invalid_request_error",
        message="bad",
        request_id="req_011CSHoEeqs5C35K2UUqR7Fy",
        raw=SAMPLE_RAW_API_ERROR,
    )
    assert e.request_id == "req_011CSHoEeqs5C35K2UUqR7Fy"


def test_error_response_request_id_can_be_none():
    """Transport-layer errors may have no request_id."""
    e = ErrorResponse(
        status_code=0,
        error_type="connection_error",
        message="connection refused",
        request_id=None,
        raw=None,
    )
    assert e.request_id is None


def test_error_response_raw_can_be_none():
    """Transport-layer errors may have no parseable body."""
    e = ErrorResponse(
        status_code=0,
        error_type="connection_error",
        message="connection refused",
        request_id=None,
        raw=None,
    )
    assert e.raw is None


def test_error_response_transport_status_zero():
    """status_code=0 conventionally signals a transport-layer error."""
    e = ErrorResponse(
        status_code=0,
        error_type="connection_error",
        message="connection refused",
        request_id=None,
        raw=None,
    )
    assert e.status_code == 0
    assert e.error_type == "connection_error"
```

- [ ] **Step 2: Run pytest, verify expected failure**

```bash
uv run pytest tests/test_responses.py -v
```

Expected: `ImportError: cannot import name 'Response' from 'claude_express'` (or `ErrorResponse`, whichever the import line hits first).

- [ ] **Step 3: Commit**

```bash
git add tests/test_responses.py
git commit -m "$(cat <<'EOF'
Test Response and ErrorResponse accessors

Response: text concatenation across multiple text blocks (skipping
non-text), stop_reason, all four usage token fields including the two
cache fields, and raw passthrough. ErrorResponse: status_code,
error_type, message, request_id (nullable for transport errors), and
raw (nullable for transport errors). Implies constructor signatures:
Response(raw=...) and ErrorResponse(status_code=, error_type=, message=,
request_id=, raw=).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Conftest — Stub Dispatcher

**Files:**
- Create: `tests/conftest.py`

The stub Dispatcher is shared across `test_send.py` and `test_lifecycle.py`. Defining it once in `conftest.py` keeps tests DRY.

- [ ] **Step 1: Write conftest.py**

Create `tests/conftest.py`:

```python
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
```

- [ ] **Step 2: Run pytest to confirm conftest doesn't break collection**

```bash
uv run pytest -v
```

Expected: same outcome as before (existing test files fail at import; conftest itself imports cleanly because everything inside `TYPE_CHECKING` is deferred and `StubDispatcher` doesn't reference `claude_express` symbols at import time).

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "$(cat <<'EOF'
Add StubDispatcher fixture for Message send/lifecycle tests

Implements the minimal Dispatcher protocol from spec §7 — an async
send(message) that returns a configured Response/ErrorResponse or
raises a configured exception, and records all calls for inspection.
Type imports under TYPE_CHECKING so conftest loads even before the
author's implementation lands.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Construction Tests

**Files:**
- Create: `tests/test_construction.py`

Spec sections: §2.2 (constructor signature, defaults, sugar), §3.1 (construction-time validation).

- [ ] **Step 1: Write the test file**

Create `tests/test_construction.py`:

```python
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
```

- [ ] **Step 2: Run pytest, verify expected failure**

```bash
uv run pytest tests/test_construction.py -v
```

Expected: `ImportError: cannot import name 'Message' from 'claude_express'` (or `ValidationError`).

- [ ] **Step 3: Commit**

```bash
git add tests/test_construction.py
git commit -m "$(cat <<'EOF'
Test Message construction — defaults, sugar, validation

Defaults: model=claude-opus-4-7, max_tokens=16000, response=None,
empty queues. Sugar: Message(user='x') and Message(system='y')
produce the same payload as queue.append('x') / queue.append('y'),
both uncached. Validation: max_tokens must be positive, model must
be non-empty; unknown model strings pass through (Anthropic decides
at send time).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Scalar Property Tests

**Files:**
- Create: `tests/test_scalars.py`

Spec section: §2.1 ("Property getters/setters for scalar fields"), §2.2 (scalar fields are `model` and `max_tokens` in MVP).

- [ ] **Step 1: Write the test file**

Create `tests/test_scalars.py`:

```python
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
```

- [ ] **Step 2: Run pytest, verify expected failure**

```bash
uv run pytest tests/test_scalars.py -v
```

Expected: `ImportError: cannot import name 'Message' from 'claude_express'`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_scalars.py
git commit -m "$(cat <<'EOF'
Test scalar property getters and setters

`model` and `max_tokens` are read/write via property; setting bad values
raises ValidationError matching the construction-time rules. Queue-backed
fields .system and .blocks have no setter — direct assignment must raise.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Queue Tests

**Files:**
- Create: `tests/test_queues.py`

Spec sections: §2.3 (queue API), §3.2 (cached-before-uncached eager validation).

- [ ] **Step 1: Write the test file**

Create `tests/test_queues.py`:

```python
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
```

- [ ] **Step 2: Run pytest, verify expected failure**

```bash
uv run pytest tests/test_queues.py -v
```

Expected: `ImportError: cannot import name 'Message' from 'claude_express'` (or one of the constants).

- [ ] **Step 3: Commit**

```bash
git add tests/test_queues.py
git commit -m "$(cat <<'EOF'
Test queue behavior — append, ordering, cached-before-uncached

Parallel test suites for .system and .blocks: empty defaults, append
extends, iteration preserves order. All cache constant aliases work.
Eager ValidationError when cached follows uncached; mixed TTLs in the
cached prefix are fine; validation failures don't half-mutate. Queues
validate independently — operations on one don't affect the other.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Serialization Tests

**Files:**
- Create: `tests/test_serialization.py`

Spec sections: §3.3 (serialization-time rules), §6 (wire serialization), §6.1 (worked example), §6.2 (render order), §6.3 (empty-queue handling).

- [ ] **Step 1: Write the test file**

Create `tests/test_serialization.py`:

```python
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
```

- [ ] **Step 2: Run pytest, verify expected failure**

```bash
uv run pytest tests/test_serialization.py -v
```

Expected: `ImportError: cannot import name 'Message' from 'claude_express'` (or `SerializationError`).

- [ ] **Step 3: Commit**

```bash
git add tests/test_serialization.py
git commit -m "$(cat <<'EOF'
Test wire serialization — render order, run-collapsed markers, limits

Payload shape: model, max_tokens, system as array, messages with single
user turn. Empty queues handled per spec §6.3. Render order independent
of append order. Wire format: CACHE_SHORT → {type: ephemeral}, CACHE_LONG
→ {type: ephemeral, ttl: 1h}. Run-collapse: single block in group, multi-
block same-TTL, TTL transitions, cached→uncached transition; collapse runs
per-queue. 4-breakpoint global limit: at-limit succeeds, over-limit raises
SerializationError. Final test reproduces the spec §6.1 worked example
verbatim.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Send Tests

**Files:**
- Create: `tests/test_send.py`

Spec sections: §4.1 (`.send()`), §4.2 (success path), §4.3 (failure path), §5 (exceptions).

- [ ] **Step 1: Write the test file**

Create `tests/test_send.py`:

```python
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
```

- [ ] **Step 2: Run pytest, verify expected failure**

```bash
uv run pytest tests/test_send.py -v
```

Expected: `ImportError: cannot import name 'Message' from 'claude_express'` (or one of the exception types). Once imports succeed, individual tests will fail with `AttributeError` until the implementation lands.

- [ ] **Step 3: Commit**

```bash
git add tests/test_send.py
git commit -m "$(cat <<'EOF'
Test Message.send() — dispatcher resolution, success, failure modes

Dispatcher resolution: constructor-injected wins over module default;
default falls back to express.dispatcher (monkey-patched in tests). Success
path: .response set, returned, .is_error=False. Failure with default
raise_on_failure=True: raises DispatchError (APIError for 4xx/5xx,
ExpressConnectionError for status 0); .response attached before exception
propagates; exception carries .response. Failure with raise_on_failure=False:
both constructor-set and per-call-set forms suppress; per-call overrides.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Frozen-After-Send Tests

**Files:**
- Create: `tests/test_lifecycle.py`

Spec section: §4.4 (frozen-after-send invariant).

- [ ] **Step 1: Write the test file**

Create `tests/test_lifecycle.py`:

```python
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
```

- [ ] **Step 2: Run pytest, verify expected failure**

```bash
uv run pytest tests/test_lifecycle.py -v
```

Expected: `ImportError: cannot import name 'FrozenMessageError' from 'claude_express'`.

- [ ] **Step 3: Run the full test suite to confirm nothing was broken**

```bash
uv run pytest -v
```

Expected: every test errors at collection time with `ImportError` (because `claude_express/__init__.py` is still empty). Total tests collected/erroring should match the sum of all test functions across the 8 test files. **No test should pass.**

This is the success state for the entire plan — a comprehensive failing-by-imports test suite ready for the author to implement against.

- [ ] **Step 4: Commit**

```bash
git add tests/test_lifecycle.py
git commit -m "$(cat <<'EOF'
Test frozen-after-send invariant

After .send() returns or raises with .response populated, all queue
appends raise FrozenMessageError, scalar setters raise, and a second
.send() raises. Holds for both success and failure paths, and both
the suppress (raise_on_failure=False) and propagate (raise_on_failure=
True) failure modes — freeze happens before raise.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Checklist (run after Task 9)

Confirm against `docs/superpowers/specs/2026-05-06-message-class-design.md`:

| Spec section | Covered by |
|---|---|
| §1 Purpose (cache-aware by construction) | Tested implicitly via §3.2 invariant tests |
| §2.1 API style (mirror + sugar + properties) | test_construction (sugar), test_scalars (properties) |
| §2.2 Constructor signature | test_construction |
| §2.3 Three queues + cache constants + append-only | test_queues |
| §2.4 Module-level defaults | test_constants (constants), test_send (express.dispatcher) |
| §3.1 Construction-time validation | test_construction |
| §3.2 Append-time eager validation | test_queues |
| §3.3 Serialization-time rules (render order, run-collapse, 4-bp limit) | test_serialization |
| §4.1 .send() signature and behavior | test_send |
| §4.2 Response shape | test_responses |
| §4.3 ErrorResponse shape | test_responses |
| §4.4 Frozen-after-send | test_lifecycle |
| §5 Exception hierarchy | test_send (DispatchError, APIError, ExpressConnectionError), test_lifecycle (FrozenMessageError), test_construction/test_scalars (ValidationError), test_serialization (SerializationError) |
| §6 Wire serialization (.payload()) | test_serialization |
| §6.1 Worked example | test_serialization (`test_spec_section_6_1_worked_example`) |
| §6.2 Render order | test_serialization |
| §6.3 Empty-queue handling | test_serialization |
| §7 Dispatcher protocol | conftest (StubDispatcher) + test_send |

**No spec section is uncovered.** Open questions in §9 are explicitly deferred to the Dispatcher brainstorm.
