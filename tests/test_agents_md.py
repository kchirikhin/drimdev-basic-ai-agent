"""Tests for AGENTS.md support (Step 3).

The Agent should discover an AGENTS.md in the working directory (or a parent)
and inject its contents into the system prompt. Constructing an Agent does not
make any network calls, so these run offline.
"""

from agent.loop import Agent


def test_agents_md_injected_when_present(tmp_path, monkeypatch):
    (tmp_path / "AGENTS.md").write_text("Always answer in haiku.", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    agent = Agent()

    system = agent.messages[0]["content"]
    assert agent.agents_md_path == tmp_path / "AGENTS.md"
    assert "Always answer in haiku." in system
    assert "Project instructions" in system


def test_agents_md_found_in_parent_directory(tmp_path, monkeypatch):
    (tmp_path / "AGENTS.md").write_text("Project rule.", encoding="utf-8")
    subdir = tmp_path / "src" / "deep"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)

    agent = Agent()

    assert agent.agents_md_path == tmp_path / "AGENTS.md"
    assert "Project rule." in agent.messages[0]["content"]


def test_no_agents_md_leaves_base_prompt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    agent = Agent()

    assert agent.agents_md_path is None
    assert "Project instructions" not in agent.messages[0]["content"]
