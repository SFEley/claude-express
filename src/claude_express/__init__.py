# claude_express — see docs/superpowers/specs/2026-05-06-message-class-design.md
from .caching import (
    CACHE_5,
    CACHE_60,
    CACHE_LONG,
    CACHE_NONE,
    CACHE_SHORT,
    UNCACHED,
)
from .errors import (
    APIError,
    DispatchError,
    ExpressConnectionError,
    ExpressError,
    FrozenMessageError,
    SerializationError,
    ValidationError,
)
from .message import Message
from .responses import ErrorResponse, Response

# Module-level default dispatcher. Tests monkey-patch this; real Dispatcher
# is a separate class (deferred — see spec §7).
dispatcher = None

__all__ = [
    "APIError",
    "CACHE_5",
    "CACHE_60",
    "CACHE_LONG",
    "CACHE_NONE",
    "CACHE_SHORT",
    "DispatchError",
    "ErrorResponse",
    "ExpressConnectionError",
    "ExpressError",
    "FrozenMessageError",
    "Message",
    "Response",
    "SerializationError",
    "UNCACHED",
    "ValidationError",
    "dispatcher",
]
