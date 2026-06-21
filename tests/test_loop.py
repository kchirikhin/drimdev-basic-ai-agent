"""Tests for the agent loop, especially robustness to blank model responses.

The local model intermittently returns a degenerate message (no text and no tool
call). These tests drive the loop with a scripted fake client so the behaviour is
deterministic and offline.
"""

from types import SimpleNamespace

from agent.loop import BLANK_RETRIES, EMPTY_REPLY_NOTICE, Agent


def _text(content):
    return SimpleNamespace(content=content, tool_calls=None)


def _tool_call(name, arguments):
    return SimpleNamespace(
        id="call-1",
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def _with_tools(*calls):
    return SimpleNamespace(content=None, tool_calls=list(calls))


class _FakeClient:
    """Returns the scripted messages one per `create` call, tracking the count."""

    def __init__(self, scripted_messages):
        self._messages = list(scripted_messages)
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **_kwargs):
        message = self._messages[self.calls]
        self.calls += 1
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _make_agent(tmp_path, monkeypatch, scripted):
    monkeypatch.chdir(tmp_path)
    agent = Agent()
    agent.client = _FakeClient(scripted)
    return agent


def test_blank_response_is_retried_then_succeeds(tmp_path, monkeypatch):
    agent = _make_agent(tmp_path, monkeypatch, [_text(""), _text("   "), _text("Hi!")])

    reply = agent.chat("hello")

    assert reply == "Hi!"
    assert agent.client.calls == 3  # two blanks retried, third succeeded


def test_all_blank_returns_notice(tmp_path, monkeypatch):
    agent = _make_agent(tmp_path, monkeypatch, [_text("")] * BLANK_RETRIES)

    reply = agent.chat("hello")

    assert reply == EMPTY_REPLY_NOTICE
    assert agent.client.calls == BLANK_RETRIES  # gave up after the retry budget


def test_tool_call_then_final_text(tmp_path, monkeypatch):
    scripted = [
        _with_tools(_tool_call("write", '{"path": "out.txt", "content": "hi"}')),
        _text("Done."),
    ]
    agent = _make_agent(tmp_path, monkeypatch, scripted)
    events = []

    reply = agent.chat("make the file", on_tool_event=lambda *a: events.append(a))

    assert reply == "Done."
    assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "hi"
    assert events[0][0] == "write"  # the tool event fired
