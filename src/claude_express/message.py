"""Message class — one Anthropic /v1/messages request, plus its lifecycle.

See docs/superpowers/specs/2026-05-06-message-class-design.md.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterator

from .caching import CACHE_LONG, CACHE_SHORT
from .errors import (
    APIError,
    DispatchError,
    ExpressConnectionError,
    FrozenMessageError,
    SerializationError,
    ValidationError,
)
from .responses import ErrorResponse, Response

if TYPE_CHECKING:
    from typing import Protocol

    class Dispatcher(Protocol):
        async def send(self, message: "Message") -> Response | ErrorResponse: ...


_DEFAULT_MODEL = "claude-opus-4-7"
_DEFAULT_MAX_TOKENS = 16000
_MAX_BREAKPOINTS = 4


def _wire_cache(cache: int) -> dict:
    """Translate a cache TTL constant to its on-the-wire cache_control value."""
    if cache == CACHE_SHORT:
        return {"type": "ephemeral"}
    if cache == CACHE_LONG:
        return {"type": "ephemeral", "ttl": "1h"}
    raise SerializationError(
        f"Unsupported cache TTL: {cache!r}. Use CACHE_SHORT, CACHE_LONG, or UNCACHED."
    )


class _Queue:
    """Append-only sequence of (text, cache) pairs with eager
    cached-before-uncached enforcement.

    Holds a back-reference to its owning Message so it can refuse mutation
    after the message has been frozen by .send().
    """

    def __init__(self, owner: "Message") -> None:
        self._owner = owner
        self._items: list[tuple[str, int | None]] = []
        self._uncached_seen = False

    def append(self, text: str, *, cache: int | None = None) -> None:
        if self._owner._frozen:
            raise FrozenMessageError(
                "Cannot mutate a Message after .send() — construct a new Message."
            )
        if cache is not None and self._uncached_seen:
            raise ValidationError(
                "Cached append after an uncached append in the same queue is "
                "not allowed (would silently miss the cache). Cache the prefix, "
                "leave the suffix uncached."
            )
        # Mutate only after validation succeeds — keep failed appends atomic.
        self._items.append((text, cache))
        if cache is None:
            self._uncached_seen = True

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[tuple[str, int | None]]:
        return iter(self._items)

    def _serialized(self) -> list[dict]:
        """Render to wire format with run-collapsed cache markers.

        For each item, place a cache_control marker iff the item is cached
        AND the next item has a different cache value (different TTL, None,
        or end-of-queue). This puts exactly one marker on the LAST block of
        each contiguous same-TTL run.
        """
        out: list[dict] = []
        n = len(self._items)
        for i, (text, cache) in enumerate(self._items):
            block: dict[str, Any] = {"type": "text", "text": text}
            if cache is not None:
                next_cache = self._items[i + 1][1] if i + 1 < n else None
                if next_cache != cache:
                    block["cache_control"] = _wire_cache(cache)
            out.append(block)
        return out


class Message:
    """One Anthropic /v1/messages request and its eventual response."""

    # Class-level sentinel so __setattr__ can recognize allowed instance attrs
    # before __init__ has set _frozen. See _MUTABLE_PROPS / _INIT_DONE below.
    _frozen = False
    _init_done = False

    def __init__(
        self,
        *,
        model: str = _DEFAULT_MODEL,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        system: str | None = None,
        user: str | None = None,
        dispatcher: "Dispatcher | None" = None,
        raise_on_failure: bool = True,
    ) -> None:
        # Validate scalars eagerly.
        self._set_model(model)
        self._set_max_tokens(max_tokens)

        self._system = _Queue(self)
        self._blocks = _Queue(self)
        self._dispatcher = dispatcher
        self._raise_on_failure = raise_on_failure
        self._response: Response | ErrorResponse | None = None
        self._frozen = False

        # Sugar — uncached appends after queues are constructed.
        if system is not None:
            self._system.append(system)
        if user is not None:
            self._blocks.append(user)

        self._init_done = True

    # ----- scalar properties --------------------------------------------------

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str) -> None:
        if self._frozen:
            raise FrozenMessageError("Cannot mutate a Message after .send().")
        self._set_model(value)

    def _set_model(self, value: str) -> None:
        if not isinstance(value, str) or value == "":
            raise ValidationError("model must be a non-empty string.")
        self._model = value

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @max_tokens.setter
    def max_tokens(self, value: int) -> None:
        if self._frozen:
            raise FrozenMessageError("Cannot mutate a Message after .send().")
        self._set_max_tokens(value)

    def _set_max_tokens(self, value: int) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValidationError("max_tokens must be a positive integer.")
        self._max_tokens = value

    # ----- queues (read-only properties; no setters by design) ----------------

    @property
    def system(self) -> _Queue:
        return self._system

    @property
    def blocks(self) -> _Queue:
        return self._blocks

    @property
    def response(self) -> Response | ErrorResponse | None:
        return self._response

    # ----- payload assembly ---------------------------------------------------

    def payload(self) -> dict:
        """Render the request body for Anthropic's /v1/messages.

        Order on the wire mirrors Anthropic's render order: system → messages.
        (Tools deferred from MVP, so their slot is omitted.) Run-collapses
        cache markers per queue and enforces the 4-breakpoint global limit.
        """
        sys_blocks = self._system._serialized()
        user_blocks = self._blocks._serialized()

        marker_count = sum(1 for b in sys_blocks if "cache_control" in b)
        marker_count += sum(1 for b in user_blocks if "cache_control" in b)
        if marker_count > _MAX_BREAKPOINTS:
            raise SerializationError(
                f"Too many cache breakpoints: {marker_count} (Anthropic allows ≤ 4). "
                "Coalesce same-TTL runs or remove a breakpoint."
            )

        body: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
        }
        if sys_blocks:
            body["system"] = sys_blocks
        body["messages"] = (
            [{"role": "user", "content": user_blocks}] if user_blocks else []
        )
        return body

    # ----- send ---------------------------------------------------------------

    async def send(
        self,
        *,
        raise_on_failure: bool | None = None,
    ) -> Response | ErrorResponse:
        if self._frozen:
            raise FrozenMessageError(
                "This Message has already been sent. Construct a new Message."
            )

        raise_flag = (
            self._raise_on_failure if raise_on_failure is None else raise_on_failure
        )
        dispatcher = self._dispatcher if self._dispatcher is not None else _module_default_dispatcher()
        if dispatcher is None:
            raise DispatchError(
                "No dispatcher configured. Pass dispatcher= to Message() or set "
                "claude_express.dispatcher."
            )

        result = await dispatcher.send(self)

        # Freeze BEFORE deciding to raise — post-mortem inspection of .response
        # must work for callers using try/except around .send().
        self._response = result
        self._frozen = True

        if result.is_error and raise_flag:
            assert isinstance(result, ErrorResponse)  # for type-checkers
            if result.status_code == 0:
                raise ExpressConnectionError(response=result)
            raise APIError(response=result)

        return result

    # ----- attribute guard ---------------------------------------------------

    def __setattr__(self, name: str, value: Any) -> None:
        # Before __init__ finishes (or for our own private attrs), allow.
        if not self._init_done or name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        # Public attribute writes that aren't going through a declared property
        # setter (model, max_tokens) should be refused — including the queue
        # names, which intentionally have no setter.
        cls = type(self)
        descriptor = getattr(cls, name, None)
        if isinstance(descriptor, property) and descriptor.fset is not None:
            descriptor.fset(self, value)
            return
        raise AttributeError(
            f"{cls.__name__!s} has no settable attribute {name!r}."
        )


def _module_default_dispatcher():
    """Look up claude_express.dispatcher at call time so monkey-patching works."""
    import claude_express  # local import: avoids the circular import at module load

    return getattr(claude_express, "dispatcher", None)
