"""Skills — progressive disclosure (Step 4).

A *skill* is a folder of instructions the agent can pull in when a task calls for
it. The point is **dynamic loading**: by default only each skill's name and short
description sit in the system prompt (cheap), and the full instructions are
fetched on demand via the `load_skill` tool (so the body enters context only when
actually needed). This keeps the base prompt small while still giving the agent
deep, specialized know-how when relevant.

On disk a skill is a directory under a `skills/` folder:

    skills/
      commit-message/
        SKILL.md        # YAML-ish frontmatter (name, description) + body

The frontmatter holds `name` and `description`; everything after it is the body.
"""

import dataclasses
from pathlib import Path

SKILLS_DIRNAME = "skills"
SKILL_FILENAME = "SKILL.md"


@dataclasses.dataclass(frozen=True)
class Skill:
    """One skill: cheap metadata (always shown) + the body (loaded on demand)."""

    name: str
    description: str
    body: str


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a `---`-delimited frontmatter block from the body.

    A deliberately tiny parser (no YAML dependency): it reads simple
    `key: value` lines from the block between the first two `---` lines.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text.strip()

    meta: dict[str, str] = {}
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            for line in lines[1:i]:
                key, sep, value = line.partition(":")
                if sep:
                    meta[key.strip()] = value.strip()
            body = "\n".join(lines[i + 1 :]).strip()
            return meta, body
    # No closing delimiter: treat the whole thing as body.
    return {}, text.strip()


def _load_skill(skill_md: Path) -> Skill:
    meta, body = _parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    return Skill(
        name=meta.get("name", skill_md.parent.name),
        description=meta.get("description", ""),
        body=body,
    )


def _find_skills_dir(start: Path) -> Path | None:
    """Find the nearest `skills/` directory, searching `start` then its parents."""
    for directory in (start, *start.parents):
        candidate = directory / SKILLS_DIRNAME
        if candidate.is_dir():
            return candidate
    return None


def discover_skills(start: Path) -> list[Skill]:
    """Discover every skill (a subdir with a SKILL.md) under the skills folder."""
    skills_dir = _find_skills_dir(start)
    if skills_dir is None:
        return []
    skills = []
    for child in sorted(skills_dir.iterdir()):
        skill_md = child / SKILL_FILENAME
        if child.is_dir() and skill_md.is_file():
            skills.append(_load_skill(skill_md))
    return skills


# The on-demand loader the model calls to pull a skill's full instructions into
# context. Only added to the tool list when at least one skill exists.
LOAD_SKILL_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "load_skill",
        "description": (
            "Load the full instructions for one of the available skills (see the "
            "'Available skills' list). Call this before doing a task that matches "
            "a skill, then follow the instructions it returns."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The skill's name."}
            },
            "required": ["name"],
        },
    },
}


class SkillLibrary:
    """The session's skills: the catalog (cheap) and on-demand body loading."""

    def __init__(self, skills: list[Skill]) -> None:
        self._by_name = {s.name: s for s in skills}

    def __bool__(self) -> bool:
        return bool(self._by_name)

    @property
    def names(self) -> list[str]:
        return list(self._by_name)

    def catalog(self) -> str:
        """The compact name + description list injected into the system prompt."""
        lines = [
            "# Available skills",
            "",
            "These skills provide detailed instructions you can load on demand "
            "with the `load_skill` tool. Only load one when a task matches it.",
            "",
        ]
        lines += [f"- {s.name}: {s.description}" for s in self._by_name.values()]
        return "\n".join(lines)

    def load(self, name: str) -> str:
        """Return a skill's full body, or an error string for an unknown name."""
        skill = self._by_name.get(name)
        if skill is None:
            available = ", ".join(self._by_name) or "(none)"
            return f"Error: unknown skill '{name}'. Available: {available}"
        return skill.body
