"""Tests for subagents — delegation with context isolation (Step 5)."""

from types import SimpleNamespace

from agent import subagents
from agent.loop import Agent


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
    def __init__(self, scripted_messages):
        self._messages = list(scripted_messages)
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **_kwargs):
        message = self._messages[self.calls]
        self.calls += 1
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_main_agent_has_task_tool(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    agent = Agent()
    assert any(t["function"]["name"] == "task" for t in agent.tools)


def test_subagent_cannot_delegate_further(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sub = Agent(depth=subagents.MAX_DEPTH)
    assert not sub.can_delegate
    assert all(t["function"]["name"] != "task" for t in sub.tools)


def test_subagent_gets_role_note_in_system_prompt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sub = Agent(depth=1)
    assert "You are a subagent" in sub.messages[0]["content"]


def test_task_tool_delegates_and_returns_only_summary(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Script, in call order: main asks to delegate, subagent answers, main wraps up.
    scripted = [
        _with_tools(_tool_call("task", '{"description": "do the thing"}')),
        _text("SUBRESULT: did the thing"),
        _text("All done."),
    ]
    fake = _FakeClient(scripted)
    # Both the main agent and the spawned subagent build their client via
    # get_client, so patching it shares this one fake across both.
    monkeypatch.setattr("agent.loop.get_client", lambda: fake)

    agent = Agent()
    events: list = []
    reply = agent.chat("please delegate", on_tool_event=lambda *a: events.append(a))

    assert reply == "All done."
    # The subagent's summary came back through the task tool result...
    task_events = [e for e in events if e[0] == "task"]
    assert task_events and "SUBRESULT" in task_events[0][2]
    # ...but the subagent's own messages never entered the main context.
    main_contents = [m.get("content") for m in agent.messages]
    assert not any("You are a subagent" in (c or "") for c in main_contents)
