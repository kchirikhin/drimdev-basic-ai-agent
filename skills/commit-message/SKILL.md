---
name: commit-message
description: Write a git commit message for a described code change.
---

# Commit message skill

When asked to write a git commit message, follow these rules exactly:

- Use the Conventional Commits format: `<type>: <summary>`.
- `type` is one of: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.
- ALWAYS put the ticket tag `[DRIM]` at the start of the summary, right after
  the colon.
- Keep the summary under 60 characters, in the imperative mood ("add", not
  "added").
- Output only the single commit-message line — no extra prose.

Example: `feat: [DRIM] add dynamic skill loading`
