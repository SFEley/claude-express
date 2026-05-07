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
