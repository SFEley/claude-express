# `Message` Class — MVP Design

**Status:** Approved for test-first implementation. Tests will be written by Claude; the `Message` class will be implemented by the author against the test suite.

**Scope:** First class in `claude-express`. Holds the data and lifecycle for a single Anthropic `/v1/messages` request, plus the response after it returns.

**Out of scope (deferred):** `Thread` (multi-turn subclass), `Dispatcher` (next class — stubbed at the network boundary for these tests), tools, non-text content blocks, `thinking`, `output_config`, `metadata`, `stop_sequences`, `stream`, `tool_choice`, `Message.copy()`/fork.

---

## 1. Purpose

A `Message` is one Anthropic API request: model + max_tokens + system + user content + (eventually) tools, plus the response after sending. It is the foundation for every higher-level capability the library will offer (prewarming, batching, multi-turn threads).

The class is cache-aware by construction: it makes invalid prompt-cache placements structurally impossible by enforcing a per-queue *cached-before-uncached* invariant eagerly. This mirrors prompt caching's prefix-match rule — once any byte changes in the prefix, downstream cache breakpoints can't hit, so allowing cached content after uncached content would only produce silent cache misses.

## 2. Public API shape

### 2.1 API style

- **Mirror Anthropic exactly + ergonomic shortcuts.** Constructor accepts both Anthropic-canonical kwargs (`model`, `max_tokens`) and ergonomic sugar (`user="..."`, `system="..."`).
- **Property getters/setters for scalar fields** (`msg.model`, `msg.max_tokens`) in addition to constructor kwargs. Property setters do not exist for queue-backed fields (would violate append-only).
- The library mirrors Anthropic's actual render order at serialization time: **`tools → system → messages`**, regardless of the order the user appended things.

### 2.2 Constructor

```python
Message(
    *,
    model: str = "claude-opus-4-7",
    max_tokens: int = 16000,
    system: str | None = None,    # sugar — uncached append to .system queue
    user: str | None = None,      # sugar — uncached append to .blocks queue
    dispatcher: "Dispatcher | None" = None,
    raise_on_failure: bool = True,
)
```

- `system=` and `user=` are sugar for `msg.system.append(...)` and `msg.blocks.append(...)` respectively. **Both are uncached.** To cache, use the queue methods directly.
- `dispatcher=None` defers to the module-level lazy default `express.dispatcher` at send time.
- `raise_on_failure=True` causes `.send()` to raise on failure; `False` suppresses the exception (`.response` is still set to an `ErrorResponse`).

### 2.3 Three independent queues

| Queue | MVP | What it holds |
|---|---|---|
| `message.tools` | ❌ Deferred entirely | (will hold tool definitions later) |
| `message.system` | ✅ String-only | System prompt content blocks |
| `message.blocks` | ✅ String-only | User-turn content blocks (single user turn — no multi-turn in MVP) |

Each queue is **append-only** with one method:

```python
queue.append(text: str, *, cache: int | None = None)
```

- `cache` accepts:
  - `CACHE_SHORT` = `CACHE_5` = 5 — 5-minute TTL → wire `cache_control: {"type": "ephemeral"}` (5-min is Anthropic's default; no `ttl` field on the wire)
  - `CACHE_LONG` = `CACHE_60` = 60 — 1-hour TTL → wire `cache_control: {"type": "ephemeral", "ttl": "1h"}`
  - `UNCACHED` = `CACHE_NONE` = `None`
- Aliases are *value-identical*: `CACHE_SHORT is CACHE_5` is `True`. Do not use intermediate values; only the constants and `None` are valid.

Queues do not expose insertion at arbitrary positions, removal, mutation of existing entries, or reordering. Iteration and length inspection (`len(msg.system)`, `for block in msg.blocks`) are fine and read-only.

### 2.4 Module-level defaults

```python
import claude_express as express
express.dispatcher        # lazily-constructed default Dispatcher singleton
express.CACHE_SHORT       # = express.CACHE_5 = 5
express.CACHE_LONG        # = express.CACHE_60 = 60
express.UNCACHED          # = express.CACHE_NONE = None
express.Message           # the class itself
express.Response          # success response type
express.ErrorResponse     # error response type
```

## 3. Validation rules

### 3.1 Construction-time

- `max_tokens` must be a positive integer.
- `model` must be a non-empty string. (Express does not enforce known model IDs — Anthropic will reject unknown models at send time.)

### 3.2 Append-time (eager)

For each queue independently: **a cached append after an uncached append raises immediately**, at the offending `.append()` call. Different TTLs within the cached prefix are allowed (e.g., `CACHE_LONG` followed by `CACHE_SHORT` is fine — both are cached). Only the cached → uncached transition is constrained.

```python
msg.system.append("a", cache=CACHE_5)   # OK — first cached
msg.system.append("b", cache=CACHE_60)  # OK — different TTL but still cached
msg.system.append("c")                   # OK — cached → uncached transition
msg.system.append("d", cache=CACHE_5)   # ❌ raises: cached after uncached
```

Each queue tracks its own state — appending uncached to `.blocks` does *not* affect what `.system` will accept.

### 3.3 Serialization-time

When `.send()` (or any internal payload assembly) walks the queues, the library:

1. Renders in `tools → system → messages` order.
2. **Run-collapses cache markers**: groups contiguous cached blocks of the same TTL within each queue, places one `cache_control` marker on the *last* block of each group.
3. Counts total markers across all queues. **If > 4, raises** at serialization (Anthropic's hard limit).

The marker on the last system block, by virtue of render order, defines a breakpoint covering `tools + system`. This is documented behavior, not a bug. (Future doc note: "caching system implicitly caches tools that come before it.")

## 4. Send and response lifecycle

### 4.1 `.send()`

```python
async def send(self, *, raise_on_failure: bool | None = None) -> "Response | ErrorResponse"
```

- Per-call `raise_on_failure` overrides the constructor default if provided.
- Resolves the dispatcher: `self._dispatcher` if set on construction, else `express.dispatcher` (lazy default).
- Submits `self` to the dispatcher.
- On success: `.response` is set to a `Response`. Returns `.response`.
- On failure: `.response` is set to an `ErrorResponse`. If `raise_on_failure` is True (default): raises `ExpressError` (or appropriate subclass — see §5). If False: returns `.response` without raising.

### 4.2 `Response` — successful response shape

| Property | Type | Notes |
|---|---|---|
| `.is_error` | `bool` (always `False`) | |
| `.text` | `str` | Concatenation of all `text`-typed blocks in `content`. |
| `.stop_reason` | `str` | `"end_turn"`, `"max_tokens"`, `"stop_sequence"`, etc. |
| `.usage.input_tokens` | `int` | Uncached input tokens billed at full rate. |
| `.usage.output_tokens` | `int` | Output tokens. |
| `.usage.cache_read_input_tokens` | `int` | Tokens served from cache (~0.1× cost). |
| `.usage.cache_creation_input_tokens` | `int` | Tokens written to cache (~1.25× / 2× cost depending on TTL). |
| `.raw` | `dict` | The underlying parsed-JSON response from Anthropic, untouched. |

### 4.3 `ErrorResponse` — failure response shape

| Property | Type | Notes |
|---|---|---|
| `.is_error` | `bool` (always `True`) | |
| `.status_code` | `int` | HTTP status code (4xx, 5xx, or 0 for network errors with no response). |
| `.error_type` | `str` | Anthropic's `error.type` string (e.g., `"invalid_request_error"`, `"rate_limit_error"`, `"overloaded_error"`). `"connection_error"` for transport-layer failures with no body. |
| `.message` | `str` | Human-readable error text. |
| `.request_id` | `str \| None` | From the `request-id` header if present. |
| `.raw` | `dict \| None` | Underlying response body if parseable; `None` for transport errors. |

### 4.4 Frozen-after-send

Once `.send()` returns or raises with `.response` set:

- All queue `.append()` calls raise.
- All scalar property setters raise (`msg.model = "..."`).
- A second `.send()` call raises.

There is no fork/copy primitive in MVP — to send a similar message, construct a new one.

## 5. Exceptions

A small hierarchy. Exact class names are flexible — these are the semantic categories the tests rely on:

```
ExpressError                       # base class
├── ValidationError                # construction-time and append-time validation
├── FrozenMessageError             # mutation or re-send after .send()
├── SerializationError             # >4 cache breakpoints across queues
└── DispatchError                  # base for send-time failures
    ├── APIError                   # 4xx / 5xx from Anthropic; carries .response (ErrorResponse)
    └── ConnectionError            # network / transport failure; carries .response (ErrorResponse)
```

`DispatchError` subclasses always have `.response` set on the originating Message *and* carry it on the exception, so a try/except can grab the `ErrorResponse` either way.

## 6. Wire serialization

The `Message` knows how to produce the JSON request body. This is exposed as a method (or property — implementation choice) for testing without sending:

```python
msg.payload() -> dict
```

Returns a dict matching Anthropic's `/v1/messages` request body. Tests will assert the exact shape against fixed inputs.

### 6.1 Worked example

```python
msg = Message(model="claude-opus-4-7", max_tokens=16000)
msg.system.append("You are a tutor.", cache=CACHE_60)
msg.system.append("Always cite sources.", cache=CACHE_60)
msg.system.append("Today's session is about geometry.", cache=CACHE_5)
msg.blocks.append("What is the area of a triangle?")

msg.payload() == {
    "model": "claude-opus-4-7",
    "max_tokens": 16000,
    "system": [
        {"type": "text", "text": "You are a tutor."},
        {
            "type": "text",
            "text": "Always cite sources.",
            "cache_control": {"type": "ephemeral", "ttl": "1h"},   # last of the CACHE_60 group
        },
        {
            "type": "text",
            "text": "Today's session is about geometry.",
            "cache_control": {"type": "ephemeral"},                # last (only) of the CACHE_5 group
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

Two breakpoints used (one per cached TTL group). System block 0 is uncached on the wire because it's not the last block of its group.

### 6.2 Render order

Queues serialize in `tools → system → messages` order, regardless of the user's append order. (Tools deferred from MVP, so MVP serialization is `system → messages` only.)

### 6.3 Empty-queue handling

- Empty `.system` queue → `system` key omitted from payload.
- Empty `.blocks` queue → `messages` key is `[]` (Anthropic will reject; this is a user error surfaced as `APIError` from the API, not pre-validated).

## 7. Dispatcher protocol (stub for tests)

The `Dispatcher` class is a separate brainstorm. For testing `Message`, the tests rely on this minimal dispatcher protocol:

```python
class Dispatcher(Protocol):
    async def send(self, message: Message) -> Response | ErrorResponse: ...
```

That is: a dispatcher has an async `send` method that takes a Message and returns a `Response` or `ErrorResponse`. **`Message.send()` is responsible for setting `self.response` from the dispatcher's return value, freezing the message, and raising-or-not based on `raise_on_failure`.** The dispatcher does not need to know about freezing or about the `raise_on_failure` flag — those are Message concerns.

For tests:
- `express.dispatcher` is monkey-patched to a stub that records calls and returns a canned `Response` or `ErrorResponse`.
- Constructor-injected dispatchers override the default — tested directly.

## 8. Tests — what they will cover

The test suite exercises every behavior above. Organized by concern:

1. **Defaults and construction**
   - Default `model` is `"claude-opus-4-7"`.
   - Default `max_tokens` is `16000`.
   - `Message()` with no args is valid.
   - `Message(max_tokens=0)` raises `ValidationError`.
   - `Message(model="")` raises `ValidationError`.

2. **Constructor sugar**
   - `Message(user="hi")` produces the same `.payload()` as `Message()` followed by `msg.blocks.append("hi")`.
   - `Message(system="x")` produces the same `.payload()` as `Message()` followed by `msg.system.append("x")`.
   - Sugar values are uncached.

3. **Property getters/setters**
   - `msg.model = "claude-haiku-4-5"` updates the field; `.payload()` reflects it.
   - `msg.max_tokens = 8000` updates and reflects.
   - Property reads return what was set.

4. **Cache constants**
   - `CACHE_SHORT is CACHE_5 is 5` (and likewise for `CACHE_LONG`/`CACHE_60`/`60`, `UNCACHED`/`CACHE_NONE`/`None`).
   - All three name forms work as the `cache=` argument.

5. **Queue append — happy path**
   - `msg.system.append("a")` extends the queue.
   - `len(msg.system)` reflects appended blocks.
   - Iteration order matches insertion order.

6. **Queue append — cached-before-uncached eager validation**
   - For each of `system` and `blocks`: appending cached after uncached raises `ValidationError` *at the offending append*.
   - Different TTLs in the cached prefix are allowed (`CACHE_LONG` then `CACHE_SHORT`).
   - The two queues are independent: uncached append in `.blocks` does not affect `.system` validation.

7. **Serialization — render order**
   - With items appended to both `.system` and `.blocks`, payload has `system` before `messages` regardless of append order.

8. **Serialization — run-collapsed marker placement**
   - Single cached block in `.system` → marker on that block.
   - Two consecutive same-TTL cached blocks → marker only on the second.
   - Three blocks: `CACHE_60`, `CACHE_5`, uncached → marker on block 0 (end of CACHE_60 run), marker on block 1 (end of CACHE_5 run), no marker on block 2.
   - Same logic for `.blocks` queue.

9. **Serialization — TTL on the wire**
   - `CACHE_5` → `cache_control: {"type": "ephemeral"}` (no `ttl` field).
   - `CACHE_60` → `cache_control: {"type": "ephemeral", "ttl": "1h"}`.

10. **Serialization — 4-breakpoint global limit**
    - Construction that produces ≤4 markers serializes successfully.
    - Construction that produces >4 markers raises `SerializationError` from `.payload()` and from `.send()`.

11. **`.send()` — dispatcher resolution**
    - With no dispatcher injected, `.send()` calls `express.dispatcher.send(self)`.
    - With `Message(dispatcher=stub)`, `.send()` calls `stub.send(self)`, not the default.
    - The default dispatcher is constructed lazily — tests can monkey-patch `express.dispatcher` after import.

12. **`.send()` — happy path**
    - Stub dispatcher returns a canned `Response`; `.response` is set; `.send()` returns the same `Response`.

13. **`.send()` — failure with `raise_on_failure=True` (default)**
    - Stub dispatcher returns `ErrorResponse`; `.send()` raises an `ExpressError` subclass.
    - `.response` is still set to the `ErrorResponse` after the exception (post-mortem inspection works).
    - The exception carries the same `ErrorResponse` (accessible via `e.response`).

14. **`.send()` — failure with `raise_on_failure=False`**
    - Per-construction (`Message(raise_on_failure=False)`) and per-call (`.send(raise_on_failure=False)`).
    - Stub dispatcher returns `ErrorResponse`; `.send()` returns it without raising.
    - `.response` is set.

15. **`Response` accessors**
    - `.is_error` is `False`.
    - `.text` concatenates text blocks from the raw content.
    - `.stop_reason`, `.usage.*` (all four token fields including the two cache fields) read through.
    - `.raw` returns the underlying dict.

16. **`ErrorResponse` accessors**
    - `.is_error` is `True`.
    - All fields populated correctly from the raw error payload.
    - `request_id` is `None` when the header was absent.
    - `.raw` is `None` for transport-layer errors with no body.

17. **Frozen-after-send invariant**
    - After `.send()` returns successfully, `msg.system.append(...)` raises `FrozenMessageError`.
    - After `.send()` returns successfully, `msg.model = "..."` raises `FrozenMessageError`.
    - After `.send()` raises (and `.response` is set to `ErrorResponse`), the same mutations raise.
    - Calling `.send()` a second time raises `FrozenMessageError`.

## 9. Open questions deferred to Dispatcher brainstorm

These belong to Dispatcher's design; flagged here so they're not forgotten:

- What does the `Dispatcher` stub in tests look like — bare async function, Protocol-conforming class, or mock? (Tests will use a small Protocol-conforming fake; documented in the test plan.)
- Does Message carry a `custom_id` for batch dispatch? (Likely yes; auto-generated; deferred to MVP+1.)
- How does the dispatcher distinguish prewarm pilots from regular sends? (Likely a kwarg or method; not Message's concern.)

## 10. Out of scope (deferred)

- **Tools**: no `.tools` queue at all in MVP. Will need typed Tool objects, possibly `@tool` decorator, possibly raw dicts. Future brainstorm.
- **Non-text blocks**: image, document, tool_result. Future brainstorm.
- **Typed Block classes** (`TextBlock`, `ImageBlock`, etc.) — future, when non-text blocks land.
- **Anthropic features**: `thinking`, `effort`, `output_config.format`, `output_config.task_budget`, `metadata`, `stop_sequences`, `stream`, `tool_choice`, `temperature` (removed on Opus 4.7).
- **`Thread` subclass** for multi-turn caching.
- **`Message.copy()` / fork** — without it, "send N similar" requires manual reconstruction. Acceptable for MVP because the natural caller for that pattern is `Dispatcher.send_all([...])`, which builds many Messages from a template upstream.
- **Real network in `Dispatcher`** — MVP Dispatcher is stubbed for these tests.
