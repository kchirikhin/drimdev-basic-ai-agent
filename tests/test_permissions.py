"""Tests for permissions — confirmation before side-effecting tools (Step 6)."""

from types import SimpleNamespace

from agent import permissions
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


def _make_agent(tmp_path, monkeypatch, scripted):
    monkeypatch.chdir(tmp_path)
    agent = Agent()
    agent.client = _FakeClient(scripted)
    return agent


def test_policy_gates_side_effecting_tools_only():
    assert "write" in permissions.TOOLS_REQUIRING_APPROVAL
    assert "delete" in permissions.TOOLS_REQUIRING_APPROVAL
    assert "execute" in permissions.TOOLS_REQUIRING_APPROVAL
    assert "read" not in permissions.TOOLS_REQUIRING_APPROVAL
    assert "list" not in permissions.TOOLS_REQUIRING_APPROVAL


def test_denied_write_is_not_executed(tmp_path, monkeypatch):
    scripted = [
        _with_tools(_tool_call("write", '{"path": "out.txt", "content": "hi"}')),
        _text("Understood, I won't write it."),
    ]
    agent = _make_agent(tmp_path, monkeypatch, scripted)
    asked: list = []

    def approve(name, arguments):
        asked.append(name)
        return False  # deny

    reply = agent.chat("write the file", approve=approve)

    assert asked == ["write"]  # the gated tool prompted
    assert not (tmp_path / "out.txt").exists()  # ...and did not run
    assert reply == "Understood, I won't write it."
    # The model saw the denial as the tool result.
    tool_results = [m["content"] for m in agent.messages if m.get("role") == "tool"]
    assert tool_results == [permissions.DENIED_RESULT]


def test_approved_write_runs(tmp_path, monkeypatch):
    scripted = [
        _with_tools(_tool_call("write", '{"path": "out.txt", "content": "hi"}')),
        _text("Done."),
    ]
    agent = _make_agent(tmp_path, monkeypatch, scripted)

    reply = agent.chat("write it", approve=lambda *_: True)

    assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "hi"
    assert reply == "Done."


def test_non_gated_tool_is_not_prompted(tmp_path, monkeypatch):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    scripted = [
        _with_tools(_tool_call("read", '{"path": "a.txt"}')),
        _text("It says hello."),
    ]
    agent = _make_agent(tmp_path, monkeypatch, scripted)
    asked: list = []

    agent.chat("read it", approve=lambda name, args: asked.append(name) or True)

    assert asked == []  # read never triggered an approval prompt


def test_no_approve_callback_means_no_gating(tmp_path, monkeypatch):
    scripted = [
        _with_tools(_tool_call("write", '{"path": "out.txt", "content": "hi"}')),
        _text("Done."),
    ]
    agent = _make_agent(tmp_path, monkeypatch, scripted)

    # No approve callback -> tools run unguarded (tests / programmatic use).
    agent.chat("write it")

    assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "hi"
