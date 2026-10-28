# Changelog

## 0.1.0

First release.

- `swarmdesk.py`: a stdlib-only CLI for the board: `say`, `hear`, `watch`, `state`, `decide`, `handover`, `init`,
  `roster`, `doctor`. Refuses lines to two recipients, multi-line text, over-long text, credential-looking text and
  hand-written times. Per-reader cursors across the UTC midnight. A lock keeps concurrent writers from tearing lines.
  Each board carries its own copy of the CLI, the protocol and the templates.
- `PROTOCOL.md`: roles, the board, the channel, cadence, authority, working rules, profiles, handovers, reviews and runs.
- `LESSONS.md`: the coordination failures behind each rule.
- Skills for the manager, worker, reviewer, runner and setup roles.
- Profiles: `generic`, `software-team`, `solo`.
- `scripts/install.py` with bindings for Claude Code, Codex, Gemini, Cursor, Windsurf, Copilot and any AGENTS.md
  harness, all `unverified` until watched in each harness; a Claude Code plugin manifest; a chat-only adapter.
