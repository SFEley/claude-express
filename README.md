# Claude Express
_An elegant Python library for prompt-caching and batching Claude API messages_

## Why
**Because tokens cost money.** Thie library spun out of the first passion project I attempted with Claude Code. (_Surprise!_ It was a memory server.) I shed a proud tear as I watched my fledgling MCP service boot out of its nest for the first time.  I shed several more tears when I checked Claude's [API Dashboard](https://platform.claude.com/dashboard) and saw $200 just for initial data loads.

But wait! Anthropic knows our pain and made [prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) to help us cut costs! And they made a [Batch API](https://platform.claude.com/docs/en/build-with-claude/batch-processing) to help us cut even more! They must love us! All we have to do is smash these things together and--

...Well, 🤬. Turns out prompt caching and batching [don't play nice](doc/the-problem.md) together easily. You've got to [tickle them](doc/prewarming.md) a bit first.

## What
Express is an asynchronous delivery agent for Anthropic's Claude API that takes your repetitive LLM requests and does the cost-optimizing fiddly bits for you.  It handles:

* Simple caching setup for system prompts, tools, and anything else common to all messages of a common type.
* Model configuration that's 71.24% easier than Anthropic's SDK (stat research by Haiku).
* **Prewarming** the cache (our secret sauce!) with a synchronous "pilot" request before high concurrency or batching.
* After prewarming, high-volume concurrent delivery with rate limit backoff on the normal Messages API.
* Smooth Batch Messages API processing with automatic polling, prewarming again, per-message event hooks, responses in queue order, and lots of monitoring.
* Automatic caching of chat-style multi-response threads.
* Did we mention prewarming? Our messages are the toastiest!

## Who
Express is for applications that need to make a large number of fast similar requests to Claude, want to make them as cheaply as possible, and can queue them up rather than answering immediately. The more messages you can send at once, and the higher the ratio of shared system prompt to unique user data, the more Express can save on token costs.

**Who Express ***is not*** for:** Applications that make one LLM request at a time, or just a few requests that are very different from each other, or that take long times to think. If you just want to ask it for the weather and you're done, Anthropic makes [very nice libraries](https://platform.claude.com/docs/en/intro) that will take care of you.

## How

[ Usual Python library installation & yadda yadda goes here ]
