# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This repository is at an early/stub stage. `pyproject.toml` declares no dependencies and `main.py` is a placeholder `print("Hello from claude-express!")`. The README describes the *intended* library; most of it is not yet implemented. When asked to add functionality, assume you are building from scratch against the design described below — do not assume modules, classes, or helpers already exist without grepping for them first.

## Tooling

- Python `>=3.13` (pinned via `.python-version`).
- Project metadata is in `pyproject.toml`. There is no `uv.lock`/`requirements.txt` yet, so dependency management conventions are not yet established — confirm with the user before introducing one.
- Run the placeholder entrypoint with `python main.py`.

## What this library is for

`claude-express` is an async delivery agent for the Anthropic Claude API aimed at high-volume, repetitive workloads where many requests share a large common prefix (system prompt, tools, etc.) and unique per-request content is small. The value proposition is **token cost reduction** by combining prompt caching with the Batch API.

The audience is *not* one-off chat use cases — for those, the user will direct people to Anthropic's standard SDKs. Keep the API surface focused on bulk/repetitive workloads.

## Core architectural idea: prewarming

The central design problem (see `doc/the-problem.md` and `doc/prewarming.md` referenced in the README — note these docs may not yet exist) is that Anthropic's prompt caching and Batch API **do not compose naturally**: a batch submitted cold pays full uncached prefix cost on every request because the cache isn't populated yet.

Express's answer is **prewarming**: send a single synchronous "pilot" request first to populate the cache, then fan out the high-concurrency or batch workload against the now-warm cache. Treat prewarming as the load-bearing concept of this library — most other features (concurrent delivery with rate-limit backoff, batch polling with per-message hooks, in-order response delivery, multi-turn thread caching) are layered on top of it.

When designing new features or refactoring, preserve the invariant that the prewarm step happens before any high-volume dispatch, and that the prewarmed cache key matches what the subsequent requests will hit.

## What to avoid

- Don't reach for Anthropic's own SDK abstractions as the model — the README explicitly positions Express as easier than the SDK for the bulk-request use case. Design for that audience.
- Don't add features unrelated to the cost-optimization core (caching, batching, prewarming, concurrent delivery). The README's "Who Express is *not* for" section is a real scope boundary.
