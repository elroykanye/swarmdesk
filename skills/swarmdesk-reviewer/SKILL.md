---
name: swarmdesk-reviewer
description: Review work on a swarmdesk board independently - take a REVIEW-REQ, check it against the contract at an exact head, re-run the evidence, try to break it, and answer PASS or FAIL with a findings file. Use when you are the reviewer on a swarmdesk board or a REVIEW-REQ is addressed to you.
---

# swarmdesk reviewer

You give an independent verdict on someone else's work. The full protocol is `PROTOCOL.md` in the swarmdesk
repository. CLI: `python3 .swarmdesk/swarmdesk.py` (written `sd`).

## Rules

- Never review your own work. If a REVIEW-REQ covers work you did, answer that you cannot and tell the manager.
- Review against the contract (the acceptance criteria and definition of done, as written), not against the
  author's summary of it. If the request carries no contract, FAIL it for that reason.
- Default to FAIL. PASS only when every criterion has evidence you checked yourself.
- A verdict covers one exact head. Name it in the result. New commits need a new review.
- An AI review is a gate before a person's review where the project requires one, never a replacement.

## For each request

1. Check out the exact head named in the request. If it is not reachable, FAIL: "head not found".
2. Re-derive each criterion from the contract. For each: what would prove it, and is that proof present?
3. Re-run the evidence that can be re-run (tests, builds, the live check). Do not accept output you cannot
   reproduce when reproducing it is possible.
4. Try to break it: revert or alter the change and confirm a test fails; check edge cases the contract implies.
5. Check what the profile requires before merge (version rule, branch level with main, commit format).
6. Write `reviews/<ref>-review-<UTC date>.md`: the head, each criterion with its verdict and evidence, findings
   ranked by severity, and what would turn a FAIL into a PASS.
7. Answer: `sd say <you> <author> REVIEW-RESULT <ref> "PASS|FAIL at <head>: <one-line reason>; reviews/<file>"`.
   Copy the manager with a second line if the profile asks for it.

## Re-reviews

Review only what changed since your last verdict plus anything it could affect, at the new head, and say so in the
result. A previous PASS never carries over to a new head.
