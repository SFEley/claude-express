# Claude Express
_An event-based library for prompt-caching and batching Claude API messages_

## Why
**Because tokens cost money.** This library spun out of the first passion project I attempted with Claude Code. (_Surprise!_ It was a memory server.) I shed a proud tear as I watched my fledgling MCP service boot out of its nest for the first time.  I shed several more tears when I checked Claude's [API Dashboard](https://platform.claude.com/dashboard) and saw $200 just for initial data loads.

But wait! Anthropic knows our pain and made [prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) to help us cut costs! And they made a [Batch API](https://platform.claude.com/docs/en/build-with-claude/batch-processing) to cut even more! They really love us! All we have to do is smash these things together and--

### The Problem

The cache isn't readable until at least one request _finishes_ (or begins to output, if streaming). That's fine for serial engagement, like a chat session, but many use cases involve a bunch of similar independent requests with only the instructions in common. We'd like to send those concurrently -- but if the API starts processing 100 messages with an empty cache, you're going to pay the higher cache-write costs for your starting blocks _one hundred times_ before you start to save money on reads.  It's awful.

And batches? Anthropic doesn't run your batch messages one at a time. It run as many of them concurrently as it can. If you're not careful, using cache-control in a batch can cost several times more than _not_ caching.

The answer to both is **prewarming.** Don't get concurrent until one message has written your cached instructions. It's a simple pattern, but a pain to implement over and over. Hence, Claude Express.


## What
Express is an asynchronous delivery agent for Anthropic's Claude API that takes your repetitive LLM data-proocessing requests and does the cost-optimizing fiddly bits for you. It's intentionally leaner than the [Anthropic SDK](https://platform.claude.com/docs/en/cli-sdks-libraries/overview) and _does not_ support tool use in this version; its sweet spot is sending many similar text requests and doing similar things with them as cheaply as practical.

Our top features:

* Model configuration that's 71.24% easier than Anthropic's SDK (*citation needed*).
* A clean object model (**Message** → **Messenger** → **Dispatcher**) with set-it-once logic for repeated options and text.
* High-volume concurrent delivery with rate limit backoff and transparent retries.
* Asynchronous responses that get synchronous when you read them. You can also give them handlers to tend to their own business. It's all Ractor-based and thread-safe.
* Caching by default on all instruction blocks and multi-round chats.
* **Prewarming** the cache (our secret sauce!) with a synchronous "pilot" request before high concurrency or batching.
* Smooth Batch Messages API processing with automatic polling, prewarming again, per-message hooks, responses in queue order, and lots of monitoring.
* Did we mention prewarming? Our messages are the toastiest!

The simplest example that works:

```ruby
require 'claude-express'

Express.api_key = '<YOUR_ANTHROPIC_KEY>'
puts Express << "What's up Claude?"
#=> "Not much, just here and ready. It’s a Thursday afternoon, so I’m guessing you’ve got something on your mind or you’re procrastinating on something. Which is it?"
```

### Caching

Claude Express offers set-it-once declaration of the repeated parts of your requests: tool blocks, system prompts, and instruction headers. You can add several of each, and Express will prepend them to the start of each message. These are remembered for either **five minutes** or **one hour**, and the cost savings for subsequent messages that start with the same text is... Well, see for yourself:

| Express value | Duration | First Instance Cost | Subsequent Cost |
|---|---|---|---|
| nil, false | No caching | Model rate per 1M input tokens | Model rate per 1M input tokens |
| `:5m` | 5 minutes | 125% of model rate | 1% to 2% of model rate |
| `:1h` | 60 minutes | 200% of model rate | 1% to 2% of model rate |
| `:default` (unbatched) | 5 minutes | 125% of model rate | 1% to 2% of model rate |
| `:default` (batched) | 60 minutes | 200% of model rate | 1% to 2% of model rate |

Our logic for the `:default` value is this: if you're pushing a large number of messages in real time, that "first instance" cost will only apply in occasional slow periods; but that's often enough that you'll want it close to standard price. Batches, on the other hand, may or may not start within five minutes of receipt; but they'll almost always occur within an hour, so the cost saving on more than a couple messages is guaranteed.

Anthropic allows you to set up to four caching "breakpoints." Express uses two of them by default: it will add a `{cache-control: }` directive to the _last_ block of the `system` and `header` sections. The presets are as follows:

```ruby
Express.cache_automatic = nil           # Only economical in multi-round chats
Express.cache_after_tools = nil         # It's rare to keep tools the same but change system
Express.cache_after_system = :default   # Default is :5m for individual messages, :1h when batched
Express.cache_after_header = :default   # Default is :5m for individual messages, :1h when batched
```

There are a few caveats and nitpicks, such as [minimum caching limits](https://platform.claude.com/docs/en/build-with-claude/prompt-caching#caching-strategies-and-considerations), which Express handles gracefully but throws warnings about.  See Anthropic's docs for complete dirt.

#### Automatic Caching

Anthropic's "automatic" caching is an oddball. It'll cache your _entire_ message, then on subsequent messages, it figures out how many starting blocks are in common. The use case for this is multi-round exchanges with Claude where the entire conversation is passed back-and-forth, building incrementally. We don't consider this the sweet spot for Claude Express, but we do support it:

```ruby
sender = Express::Messenger.new
sender.cache_automatic = :5m
response = sender << 'Where does Tuesday get its name from?'    # `send` also works but doesn't look as keen
puts response
response = sender << response, 'Okay, how about Wednesday?'     # Makes new message from response + string
puts response
response = sender << response, 'Cool, now tell me about Thursday!'
puts response
```


```ruby
require 'claude-express'

Express.api_key = '<YOUR_ANTHROPIC_KEY>'
Express.timeout = 5.minutes     # Non-batch messages fail after this period

sender = Express::Messenger.new  # Uses default dispatcher and settings
sender.model = 'haiku'           # Looks up and uses latest version if not given
sender.effort = 'medium'
sender.batch_size = 100             # A batch will be sent every 100 requests...
sender.batch_interval = 10.minutes  # ...or every 10 minutes, whichever comes first

# The system field provides context for the LLM's task
sender.system = "You are a helpful moderator for a bulletin board of paper airplane enthusiasts. Every topic related to designing, building, and flying paper airplanes is discussed here. Our community guidelines are as follows: [...]"

# The 'header' is a text block that precedes every message, for specific handilng instructions.
sender.header << "A message submitted to our board follows this paragraph. On a line by itself, as the first word of your response, classify this message as VALID, ABUSIVE, or SPAM. If the message is ABUSIVE, then on the following line, give your reason in a sentence of no more than 50 words. Do not add additional text for VALID or SPAM messages, and do not use any markdown or formatting."

sender.on_response do |response|
    case response.lines.first
    when /VALID/
        # Handle valid response
    when /ABUSIVE/
        # Handle abusive response
    when /SPAM/
        # Handle spam response
    else
        raise "Wrong format! #{response}"
    end
end

sender << "...message 1..."     # Sent right away to prime the cache
sender << "...message 2..."     # Batched
sender << "...message 3..."     # Batched

sender.status #=> { sent: 1, pending: 2, batched: 2, failed: 0, responses: 1 }
sender.send_batch!  # Forces batch to deliver with current messages
sleep 2.minutes     # Batch dispatcher auto-polls every minute until completed
sender.status #=> { sent: 3, pending: 0, batched: 0, failed: 0, responses: 3 }
```


### Configuration

If you're happy with the defaults, Claude Express only needs your API key to start rolling. This and every other option can be set globally on the **Express** module; or you can create your own **Dispatcher** and **Messenger** objects and configure them individually.


* We track all the model and header details so you don't have to, and give you sensible defaults.
* Essential messaging methods are defined on the top-level class object
* Validation errors are sensible and tell you what the acceptable values are.
* General model names like 'opus' use the latest version we know about. If you specify a version we _don't_ know (i.e. it just came out today), we use the [List Models API](https://platform.claude.com/docs/en/api/http/models/list) at start time to set it up, and optionally save it to a configuration file you specify.

### Dispatcher
A **Dispatcher** object sends large numbers of API calls to Anthropic quickly, using your language's best-in-class asynchronous HTTPS library.
* Rate limiting, retries, timeouts, and other connection matters are handled at this level across all API calls.
* There are three dispatcher classes built in; you're free to add others:
    * **Dispatcher::Fast** (default) - uses a leading async HTTPs library to minimize the impact of waiting for response times
    * **Dispatcher::Anthropic** - wraps the [Anthropic SDK](https://gemdocs.org/gems/anthropic/1.78.0/index.html) to send messages and process responses (less efficient but more features and reliability; necessary for multimedia content or tool use)
    * **Dispatcher::Batch** - collects messages into a batch, which it forwards to another dispatcher

### Messenger
A **Messenger** obect covers all the repeatable parts of a given flow, so your business logic can focus on the things that vary.
* Tools, system instructions, and 'header' message blocks are set here and prefixed to every message before dispatch. These are cached by default with a TTL of 5 minutes, or 1 hour if batched, which of course can be overridden.
* Data can be sent to the messenger as:
    * One or more strings, which become `text` blocks.
    * A **Message** object for high configurability (the Messenger makes one for you if you don't supply it).
    * A **Response** and one or more strings for easy multi-round chats.
    * A `#blocks` method accepts one or more JSONable objects with a `"type:"` top-level field, enabling advanced content blocks like tool use without Express having to get its hands dirty.
* Sending returns a **Response** object, wh

### Message

* Declaring tool setup, system instructions, and 'instruction' message blocks once, separately from the parts that vary.
    * These are cached by default, with 5-minute TTL for when sent in the Messages API and 1-hour in the Batch API. You can override this of course.
    * Individual messages can give different tool/system/instruction blocks or turn them off, bypassing the caching.
* Passing a single message's input and output to a handler as soon as a response comes in, whether it's using the Messages API or Batch API.
    * The handler can a , or a code block. We use the

### Caching



## Who
Express is for applications that need to make a large number of fast similar requests to Claude, want to make them as cheaply as possible, and can queue them up rather than answering immediately. The more messages you can send at once, and the higher the ratio of shared system prompt to unique user data, the more Express can save on token costs.

**Who Express ***is not*** for:** Applications that make one LLM request at a time, or just a few requests that are very different from each other, or that take long times to think. If you just want to ask it for the weather and you're done, Anthropic makes [very nice libraries](https://platform.claude.com/docs/en/intro) that will take care of you.

## How

( Usual Python library installation & yadda yadda goes here )
