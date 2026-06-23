"""Tests for the context-usage summary (the `context` command)."""

from agent import context


def test_counts_messages_by_role():
    messages = [
        {"role": "system", "content": "x" * 40},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
        {"role": "user", "content": "again"},
    ]
    summary = context.summarize_messages(messages)
    assert summary.total_messages == 4
    assert summary.by_role["user"].count == 2
    assert summary.by_role["system"].count == 1
    assert summary.by_role["assistant"].count == 1


def test_token_estimate_scales_with_length():
    short = context.summarize_messages([{"role": "user", "content": "abcd"}])
    long = context.summarize_messages([{"role": "user", "content": "abcd" * 100}])
    assert long.total_tokens > short.total_tokens
    assert short.total_tokens >= 1


def test_tool_call_payload_counts_toward_tokens():
    # An assistant message with no content but a tool_calls payload still costs.
    message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {"function": {"name": "write", "arguments": '{"path": "a.txt"}'}}
        ],
    }
    summary = context.summarize_messages([message])
    assert summary.by_role["assistant"].tokens > 0


def test_format_includes_percentage_when_window_given():
    summary = context.summarize_messages([{"role": "user", "content": "abcd" * 100}])
    text = context.format_summary(summary, window=1000)
    assert "Context usage" in text
    assert "% of 1000" in text


def test_format_without_window_has_no_percentage():
    summary = context.summarize_messages([{"role": "user", "content": "hi"}])
    text = context.format_summary(summary)
    assert "%" not in text
