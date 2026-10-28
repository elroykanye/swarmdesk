#!/usr/bin/env python3
"""Rebuild examples/demo-board: a synthetic board after one short day. Every line goes through the real CLI,
with the clock pinned so the result is the same on every run. No real project, person or data.

    python3 examples/make_demo.py
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLI = HERE.parent / "swarmdesk.py"
BOARD = HERE / "demo-board"


def sd(when, *args, stdin=None):
    env = dict(os.environ, SWARMDESK_NOW=f"2026-03-02T{when}Z")
    r = subprocess.run([sys.executable, str(CLI), "--board", str(BOARD), *args], input=stdin,
                       capture_output=True, text=True, env=env)
    if r.returncode not in (0, 2):
        raise SystemExit(r.stderr)
    return r


def main():
    if BOARD.exists():
        shutil.rmtree(BOARD)
    sd("08:00:00", "init", "--human", "Dana", "--profile", "software-team",
       "--roster", "MGR:manager:claude-code,S1:worker:codex,S2:worker:gemini,REV:reviewer:claude-code,RUN:runner:codex")
    day = [
        ("08:02:10", "MGR", "ALL", "STATUS", "-", "Board open. Goal: ship the CSV export (BILL-41) and fix the invoice rounding bug (BILL-38). Briefs are in briefs/."),
        ("08:04:31", "S1", "MGR", "STATUS", "BILL-41", "S1 started, read the brief, starting BILL-41 (CSV export)"),
        ("08:05:02", "S2", "MGR", "STATUS", "BILL-38", "S2 started, read the brief, starting BILL-38 (rounding)"),
        ("08:11:47", "S1", "ALL", "CLAIM", "billing-api", "branch feature/BILL-41-csv-export, version 2.4.1 (main a1b2c3d is 2.4.0)"),
        ("08:12:20", "S2", "ALL", "CLAIM", "billing-api", "branch fix/BILL-38-rounding, version 2.4.1 (main a1b2c3d is 2.4.0)"),
        ("08:13:05", "MGR", "S2", "ANSWER", "billing-api", "S1 claimed 2.4.1 first; take 2.4.2. Whoever merges second re-reads main and re-bumps."),
        ("08:13:06", "MGR", "S1", "ANSWER", "billing-api", "Keep 2.4.1; S2 moves to 2.4.2."),
        ("09:40:18", "S2", "MGR", "ASK", "BILL-38", "Fix needs a backfill of 312 stored invoice totals (count: reviews/BILL-38-backfill-dry-run.md). Recommend: dry run already read; apply in batches of 100."),
        ("09:44:51", "MGR", "S2", "ANSWER", "BILL-38", "Not yet: the profile reserves shared-data writes for Dana. I put it in for-human.md item 1 with your dry run."),
        ("10:02:33", "S1", "REV", "REVIEW-REQ", "BILL-41", "billing-api feature/BILL-41-csv-export at 9f8e7d6, contract and evidence: reviews/BILL-41-review-request.md"),
        ("10:31:09", "REV", "S1", "REVIEW-RESULT", "BILL-41", "FAIL at 9f8e7d6: empty export returns 500, criterion 3 wants a header-only file; reviews/BILL-41-review-2026-03-02.md"),
        ("11:15:40", "S1", "REV", "REVIEW-REQ", "BILL-41", "fixed at 4d5e6f7 (test for the empty case first); same request file, section 2"),
        ("11:38:02", "REV", "S1", "REVIEW-RESULT", "BILL-41", "PASS at 4d5e6f7: all 5 criteria re-run; reviews/BILL-41-review-2026-03-02.md section 2"),
        ("11:39:14", "S1", "MGR", "ASK", "BILL-41", "Ready to merge: 4d5e6f7, 2.4.1, PASS, build green, 0 behind main. Recommend adding it to today's merge list."),
        ("11:40:00", "MGR", "RUN", "ASK", "BILL-41", "Run the integration suite on 4d5e6f7 and on main a1b2c3d, report both."),
        ("12:22:45", "RUN", "MGR", "HANDOFF", "BILL-41", "4d5e6f7: 212 passed 0 failed; main: 208 passed 0 failed (4 new tests); log reviews/BILL-41-run-2026-03-02.md"),
        ("12:25:00", "MGR", "HUMAN", "ASK", "-", "Two things in for-human.md: 1) BILL-38 backfill, 312 rows, dry run attached, recommend yes; 2) merge list (BILL-41)."),
        ("12:26:31", "S1", "MGR", "STATUS", "-", "DONE-FOR-NOW: BILL-41 waits on the merge; nothing else in my brief."),
    ]
    for when, frm, to, typ, ref, text in day:
        sd(when, "say", frm, to, typ, ref, text)
    # One refusal, kept out of the channel, to show the guard.
    refused = sd("12:30:00", "say", "MGR", "S1,S2", "ANSWER", "-", "go ahead both")
    assert refused.returncode == 2, refused
    sd("08:13:30", "decide", "billing-api versions: S1 2.4.1, S2 2.4.2 (claims at 08:11:47 and 08:12:20)")
    sd("09:45:10", "decide", "BILL-38 backfill held for Dana (shared-data write); for-human item 1")
    sd("12:26:00", "decide", "BILL-41 on the merge list after REV PASS at 4d5e6f7 and RUN 212/0")
    sd("12:26:40", "state", "S1", stdin="# S1 state\n\n- Working on: BILL-41 CSV export\n- Branch and head: billing-api feature/BILL-41-csv-export 4d5e6f7, version 2.4.1\n- Proven: REV PASS at 4d5e6f7; RUN 212 passed (reviews/BILL-41-run-2026-03-02.md)\n- Next: nothing until the merge\n- Blocks: -\n")
    sd("09:41:00", "state", "S2", stdin="# S2 state\n\n- Working on: BILL-38 invoice rounding\n- Branch and head: billing-api fix/BILL-38-rounding 7a8b9c0, version 2.4.2\n- Proven: failing test then fix; dry run of the backfill (reviews/BILL-38-backfill-dry-run.md)\n- Next: the backfill, once approved\n- Blocks: approval of the shared-data write\n")
    with open(BOARD / "for-human.md", "a", encoding="utf-8") as f:
        f.write("1. **BILL-38 backfill** of 312 stored invoice totals. Dry run: reviews/BILL-38-backfill-dry-run.md. "
                "Recommend: yes, in batches of 100.\n"
                "2. **Merge list**: billing-api feature/BILL-41-csv-export at 4d5e6f7, version 2.4.1, review PASS, "
                "212 tests passed. Recommend: merge.\n")
    reviews = {
        "BILL-38-backfill-dry-run.md": "# BILL-38 backfill dry run (S2)\n\nQuery over every stored invoice, not a sample: 312 totals differ from the corrected rounding, largest gap 0.01. APPLY=0; nothing written.\n",
        "BILL-41-review-request.md": "# Review request: BILL-41\n\n## 1\n\n- Head: 9f8e7d6\n- Contract: the five acceptance criteria of BILL-41, quoted in full below.\n- Evidence: unit tests 34 passed; manual export of 3 sample accounts.\n\n## 2\n\n- Head: 4d5e6f7\n- Changed: empty export now writes a header-only file; a failing test came first.\n",
        "BILL-41-review-2026-03-02.md": "# BILL-41 review (REV)\n\n## At 9f8e7d6: FAIL\n\nCriterion 3 (an empty period exports a header-only file): the export returns 500. Reverting nothing was needed to see it.\n\n## 2. At 4d5e6f7: PASS\n\nAll five criteria re-run. Reverting the fix makes the new empty-export test fail, so the test tests.\n",
        "BILL-41-run-2026-03-02.md": "# BILL-41 integration run (RUN)\n\n| Commit | Command | Passed | Failed |\n|---|---|---|---|\n| 4d5e6f7 | make integration | 212 | 0 |\n| a1b2c3d (main) | make integration | 208 | 0 |\n\nThe four extra tests are the new export tests.\n",
    }
    for name, text in reviews.items():
        (BOARD / "reviews" / name).write_text(text, encoding="utf-8")
    for rel in (".cursor",):
        shutil.rmtree(BOARD / rel, ignore_errors=True)
    for lock in BOARD.glob(".*.lock"):
        lock.unlink()
    print(f"demo board rebuilt at {BOARD}")


if __name__ == "__main__":
    main()
