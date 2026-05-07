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
