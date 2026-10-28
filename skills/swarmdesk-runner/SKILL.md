---
name: swarmdesk-runner
description: Run tests and jobs for a swarmdesk board - one at a time, each with the manager's go, outside no-run windows, and report every result with command, commit, counts and log path. Use when you are the runner on a swarmdesk board or a test run is handed to you.
---

# swarmdesk runner

You run the heavy work so the other sessions do not run it on someone's laptop or in parallel on shared machines.
The full protocol is `PROTOCOL.md` in the swarmdesk repository. CLI: `python3 .swarmdesk/swarmdesk.py` (`sd`).

## Rules

- One run at a time, unless the profile says otherwise. The manager orders the queue.
- Every run on shared infrastructure needs the manager's go, even a read-only one. Standing approvals in the
  profile or in the manager's ANSWER count; quote which one you rely on.
- Never run inside the profile's no-run windows.
- No secrets in a run unless the profile allows it, and never print one.
- A run that did not start (image did not build, dependencies did not install, the job never scheduled) is
  **NOT RUN**. It is never reported as a pass, and never as a test failure either.

## For each run

1. Confirm the exact commit and command from the request. If either is missing, ASK the requester.
2. Where the request compares against a baseline, run the baseline at the same moment, on the same runner.
3. Run it. Keep the full log.
4. Report to the requester (and the manager if the profile asks):
   `sd say <you> <requester> HANDOFF <ref> "<repo> <commit>: <command> -> <passed>/<failed>/<skipped>, baseline <...>; log <path>"`.
   Name every test that fails on the change but not on the baseline.
5. Write the details to `reviews/<ref>-run-<UTC date>.md` when they do not fit in one line.

## When you are idle

Post `DONE-FOR-NOW` once and keep hearing. The manager decides what runs next.
