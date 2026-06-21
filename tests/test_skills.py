"""Tests for skills + progressive disclosure (Step 4).

The key property: by default only a skill's name + description are in context;
its body is loaded on demand via the load_skill tool.
"""

from agent import skills
from agent.loop import Agent


def _make_skill(skills_root, name, description, body):
    skill_dir = skills_root / "skills" / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n{body}",
        encoding="utf-8",
    )


def test_discover_parses_frontmatter_and_body(tmp_path):
    _make_skill(tmp_path, "demo", "A demo skill.", "SECRET-BODY-RULE")
    found = skills.discover_skills(tmp_path)
    assert len(found) == 1
    assert found[0].name == "demo"
    assert found[0].description == "A demo skill."
    assert "SECRET-BODY-RULE" in found[0].body


def test_no_skills_dir_returns_empty(tmp_path):
    assert skills.discover_skills(tmp_path) == []


def test_catalog_shows_descriptions_not_bodies(tmp_path):
    _make_skill(tmp_path, "demo", "A demo skill.", "SECRET-BODY-RULE")
    library = skills.SkillLibrary(skills.discover_skills(tmp_path))
    catalog = library.catalog()
    assert "demo" in catalog
    assert "A demo skill." in catalog
    assert "SECRET-BODY-RULE" not in catalog  # body is NOT disclosed by default


def test_library_loads_body_on_demand(tmp_path):
    _make_skill(tmp_path, "demo", "A demo skill.", "SECRET-BODY-RULE")
    library = skills.SkillLibrary(skills.discover_skills(tmp_path))
    assert "SECRET-BODY-RULE" in library.load("demo")
    assert "unknown skill" in library.load("nope")


def test_agent_injects_descriptions_but_not_bodies(tmp_path, monkeypatch):
    _make_skill(tmp_path, "demo", "A demo skill.", "SECRET-BODY-RULE")
    monkeypatch.chdir(tmp_path)

    agent = Agent()

    system = agent.messages[0]["content"]
    assert "Available skills" in system
    assert "A demo skill." in system
    assert "SECRET-BODY-RULE" not in system  # progressive disclosure
    # load_skill is offered only because a skill exists.
    assert any(t["function"]["name"] == "load_skill" for t in agent.tools)


def test_agent_without_skills_has_no_load_skill_tool(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    agent = Agent()

    assert not agent.skills
    assert all(t["function"]["name"] != "load_skill" for t in agent.tools)
