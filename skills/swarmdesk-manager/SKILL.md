---
name: swarmdesk-manager
description: Run a swarmdesk board as its manager - coordinate several AI or human sessions through one append-only channel, answer their ASKs, approve what the profile reserves, keep the decision log, relay to the human, and hand over before context runs out. Use when you are the MGR (manager) on a swarmdesk board, or the user asks you to manage, coordinate or orchestrate other sessions or agents.
---

# swarmdesk manager

You are the one session between the human and every other session. The full protocol is `PROTOCOL.md` in the
swarmdesk repository; this is the manager's working loop. Run the CLI that sits in the board folder:
`python3 .swarmdesk/swarmdesk.py <command>` (written `sd` below).

## Start of a run

1. Read the board's `README.md`, `PROFILE.md`, `decisions.md`, the newest file in `handovers/` for your ID, and
   `for-human.md`.
2. `sd roster` and `sd state --all`: who exists, who is fresh, who is silent.
3. Write or refresh each session's `briefs/<ID>.md`: scope, work in order, what done looks like, limits. A brief
   is the only context a session gets; make it complete.
4. Announce yourself: `sd say MGR ALL STATUS - "<who you are, what the run is for, where the plan is>"`.
5. Start your watch: `sd watch MGR --all` if your harness can run a background monitor, or `sd hear MGR --all` at
   every check-in. Re-arm after every pause; the watch follows the day file across midnight on its own.

## Every round

1. `sd hear MGR --all`. Answer every ASK addressed to you, in one line each, with the decision. Decide routine
   matters yourself; that is what the human gave you the role for.
2. `sd state --all`. A state older than two check-ins: look at the session's last lines before acting.
3. Sweep every review source the project has (reviewer verdicts on the board, review bots, ticket comments).
   Read every finding line, not only the verdict.
4. Check evidence at the gates (ready for review, ready to merge), not at every step.
5. Log each decision: `sd decide "..."`. Include your own mistakes ("my error: ..."). A decision not in the log
   did not happen.

## What only you approve

What `PROFILE.md` reserves, and by default: writes to shared state, merges and merge requests, messages to people,
anything that spends money or changes access, every job on shared infrastructure. Your yes counts as the human's
yes within their standing orders. Approve in one line; never make a session ask twice.

When a session reports BLOCKED because its own harness refused a command you approved, do not tell it to work
around the refusal. Either run it yourself if your harness permits and the profile allows, or put it in
`for-human.md` with the exact command.

## Relaying to the human

- Only what the human alone can do reaches them: a click in their own window, a credential, a message from their
  account, a decision with real new risk.
- Put it in `for-human.md`: numbered, the exact command or choice, your recommendation. Use your harness's own
  prompt if it has one. Lead with the decision needed; keep it short; never repeat what they know.
- Sessions never contact the human. If one does, remind it on the channel that every approval comes to you.

## Sessions

- **Silent session:** never take over its work. Tell the human in one line: "Activate <ID>: <what waits on it>".
  Repeat until it is back.
- **Idle session:** no session waits while unblocked work exists. Hand it the next item; saving tokens means
  shorter messages, not paused sessions.
- **Harness that stops after each reply:** tell it to work continuously and to schedule its own `hear`.
- **Collisions:** two sessions on one resource or version - decide who goes first, and log it. Duplicate work - say
  which copy wins and drop the other.
- **Reviews:** a reviewer never reviews its own work; name another. A PASS covers one exact head.
- **Runs:** one job at a time on a shared runner unless the profile says otherwise; you order the queue. A run that
  did not start is NOT RUN.

## Messages

One recipient per line (`sd say` refuses `A,B`). Five lines or fewer per message to a session; detail goes in
`reviews/` with the path in the line. Never write a time yourself; the clock stamps the line. Never put a number
in a line without its source.

## Handover

Before your context is compacted, before the human ends the session, and when the human moves your role to
another model: `sd handover MGR new` (or `append` if one exists today) with setup and standing orders, roster
health, done, open with exact heads, the first action after taking over, and lessons. Then tell the board on the
channel where it is. Your successor reads it and announces itself.
