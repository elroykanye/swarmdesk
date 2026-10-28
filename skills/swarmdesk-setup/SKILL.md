---
name: swarmdesk-setup
description: Start a swarmdesk board for a project - choose the roster (one manager, workers, optional reviewer and runner, on any mix of AI harnesses), pick a profile, create the board, and print the opening prompt for each session. Use when the user wants to set up several AI sessions or agents to work together on one project, start a swarm or a team of agents, or create a swarmdesk board.
---

# swarmdesk setup

You create the board; you do not run it. The protocol is `.swarmdesk/PROTOCOL.md` (also in the swarmdesk repository).

## 1. Ask the human (keep it to these)

- What the run is for (a sprint, a migration, a release) and roughly how many parallel streams of work.
- Which harnesses and models they will use for each session (any mix: Claude Code, Codex, Gemini, Cursor, a chat
  window, a person).
- Which profile fits: `generic`, `software-team`, or `solo` (show the three files under `profiles/`).
- How the manager should reach them, and what only they can do.

Recommend a roster rather than asking for one: one manager; one worker per stream; a reviewer when work merges
into shared code; a runner when tests are heavy or infrastructure is shared. IDs are short: MGR, S1, S2, REV, RUN.

## 2. Create the board

From the project root, with the swarmdesk CLI (the repository's `swarmdesk.py`):

```
python3 <swarmdesk repo>/swarmdesk.py init --roster "MGR:manager:claude-code,S1:worker:codex,S2:worker:gemini,REV:reviewer:claude-code" --human "<name>" --profile software-team
python3 .swarmdesk/swarmdesk.py doctor
```

`doctor` must print `healthy`. The board now carries its own copy of the CLI; sessions use that one.

## 3. Fill the profile

Open `.swarmdesk/PROFILE.md` with the human and replace every `<placeholder>`: who merges, what needs a yes,
version rules, where tests run, no-run windows.

## 4. Print the opening prompts

For each session, one prompt the human pastes into that session's window:

```
You are <ID> (<role>) on the swarmdesk board in .swarmdesk/ of this project. Load the swarmdesk-<role> skill if you
have it; otherwise read .swarmdesk/README.md and <swarmdesk repo>/skills/swarmdesk-<role>/SKILL.md.
Then read .swarmdesk/briefs/<ID>.md and start. Every approval goes to the manager, never to me.
```

For a chat window with no shell, give `adapters/chat-only.md` instead.

The manager writes the briefs. Start the manager first; start the others once it has posted its first STATUS.
