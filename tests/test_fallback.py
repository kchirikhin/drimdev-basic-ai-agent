"""Tests for recovering tool calls emitted as text (model robustness)."""

from agent import fallback

KNOWN = {"write", "read", "execute"}


def test_parses_raw_json_object():
    content = '{"name": "write", "arguments": {"path": "a.txt", "content": "hi"}}'
    assert fallback.parse_text_tool_call(content, KNOWN) == (
        "write",
        {"path": "a.txt", "content": "hi"},
    )


def test_parses_fenced_json_with_surrounding_prose():
    content = (
        "Sure! I'll save it.\n\n"
        '```json\n{"name": "write", "arguments": {"path": "a.txt"}}\n```'
    )
    assert fallback.parse_text_tool_call(content, KNOWN) == ("write", {"path": "a.txt"})


def test_parses_arguments_given_as_json_string():
    content = '{"name": "read", "arguments": "{\\"path\\": \\"x\\"}"}'
    assert fallback.parse_text_tool_call(content, KNOWN) == ("read", {"path": "x"})


def test_accepts_parameters_as_alias_for_arguments():
    content = '{"name": "read", "parameters": {"path": "x"}}'
    assert fallback.parse_text_tool_call(content, KNOWN) == ("read", {"path": "x"})


def test_recovers_from_stray_prefix_before_json():
    content = 'ḷ\n{"name": "execute", "arguments": {"command": "ls"}}'
    assert fallback.parse_text_tool_call(content, KNOWN) == (
        "execute",
        {"command": "ls"},
    )


def test_unknown_tool_name_is_ignored():
    content = '{"name": "definitely_not_a_tool", "arguments": {}}'
    assert fallback.parse_text_tool_call(content, KNOWN) is None


def test_plain_prose_is_not_a_tool_call():
    assert fallback.parse_text_tool_call("Here is your answer: 42.", KNOWN) is None


def test_malformed_json_returns_none():
    assert fallback.parse_text_tool_call('{"name": "write", "argum', KNOWN) is None


def test_json_without_name_returns_none():
    assert fallback.parse_text_tool_call('{"foo": 1, "bar": 2}', KNOWN) is None


def test_empty_content_returns_none():
    assert fallback.parse_text_tool_call(None, KNOWN) is None
    assert fallback.parse_text_tool_call("", KNOWN) is None
