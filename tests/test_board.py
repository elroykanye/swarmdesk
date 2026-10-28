"""init, roster, state, decide, handover, doctor, and concurrent writers."""
import json
import multiprocessing
import os
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import CLI, REPO, BoardCase, run

sys.path.insert(0, str(REPO))
import swarmdesk  # noqa: E402


class Init(BoardCase):
    def test_layout(self):
        for p in ["config.json", "README.md", "swarmdesk.py", "chat", "state", "briefs", "reviews",
                  "handovers", "decisions.md", "for-human.md", "templates/brief.md", "PROTOCOL.md",
                  "PROFILE.md"]:
            self.assertTrue((self.board / p).exists(), p)
        cfg = json.loads((self.board / "config.json").read_text())
        self.assertEqual([m["id"] for m in cfg["roster"]], ["MGR", "S1", "S2", "REV", "RUN"])
        self.assertEqual(cfg["human"], "the owner")
        self.assertTrue((self.board / "briefs" / "S1.md").exists())

    def test_refuses_second_init(self):
        r = run(["init", "--roster", "MGR:manager:x"], board=self.board)
        self.assertEqual(r.returncode, 2)

    def test_board_copy_of_cli_runs_without_board_flag(self):
        r = run(["say", "S1", "MGR", "STATUS", "-", "from the board copy"], now=self.now,
                cli=self.board / "swarmdesk.py")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.chat_lines()), 1)

    def test_board_found_by_walking_up_from_cwd(self):
        sub = self.root / "src" / "deep"
        sub.mkdir(parents=True)
        env = dict(os.environ, SWARMDESK_NOW=self.now)
        env.pop("SWARMDESK_BOARD", None)
        import subprocess
        r = subprocess.run([sys.executable, str(CLI), "roster"], cwd=sub, capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("MGR", r.stdout)


class InitValidation(unittest.TestCase):
    def check(self, roster, fragment):
        with tempfile.TemporaryDirectory() as d:
            r = run(["init", "--roster", roster], board=Path(d) / ".swarmdesk")
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn(fragment, r.stderr)

    def test_exactly_one_manager(self):
        self.check("S1:worker:x", "exactly one manager")
        self.check("A:manager:x,B:manager:x", "exactly one manager")

    def test_reserved_and_duplicate_ids(self):
        self.check("ALL:manager:x", "reserved")
        self.check("MGR:manager:x,S1:worker:x,S1:worker:y", "duplicate")

    def test_unknown_role(self):
        self.check("MGR:manager:x,S1:boss:x", "role")


class Roster(BoardCase):
    def test_add(self):
        r = self.sd("roster", "add", "S3", "worker", "cursor")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.say("S3", "MGR", "STATUS", "-", "hello").returncode, 0)
        self.assertTrue((self.board / "briefs" / "S3.md").exists())

    def test_add_refuses_existing(self):
        self.assertEqual(self.sd("roster", "add", "S1", "worker", "x").returncode, 2)


class State(BoardCase):
    def test_write_and_glance(self):
        r = self.sd("state", "S1", stdin="working on PROJ-12\nnext: tests\n", now="2026-10-26T12:00:00Z")
        self.assertEqual(r.returncode, 0, r.stderr)
        text = (self.board / "state" / "S1.md").read_text()
        self.assertIn("2026-10-26T12:00:00Z", text.splitlines()[0])
        self.assertIn("working on PROJ-12", text)
        glance = self.sd("state", "--all", now="2026-10-26T12:10:00Z").stdout
        self.assertRegex(glance, r"S1\s+10 min")
        self.assertRegex(glance, r"S2\s+never")
        stale = self.sd("state", "--all", now="2026-10-26T13:00:00Z").stdout
        self.assertRegex(stale, r"S1\s+60 min\s+STALE")


class Decide(BoardCase):
    def test_appends_clock_stamped_lines(self):
        self.sd("decide", "S1 takes the billing repo", now="2026-10-26T12:01:00Z")
        self.sd("decide", "--by", "MGR", "my error: wrong head quoted", now="2026-10-26T12:02:00Z")
        lines = [l for l in (self.board / "decisions.md").read_text().splitlines() if l.startswith("- ")]
        self.assertEqual(lines, ["- 2026-10-26 12:01:00Z | MGR | S1 takes the billing repo",
                                 "- 2026-10-26 12:02:00Z | MGR | my error: wrong head quoted"])


class Handover(BoardCase):
    def test_new_then_append_never_rewrites(self):
        r = self.sd("handover", "MGR", "new", stdin="first state\n", now="2026-10-26T14:00:00Z")
        self.assertEqual(r.returncode, 0, r.stderr)
        path = Path(r.stdout.strip())
        before = path.read_bytes()
        r = self.sd("handover", "MGR", "append", stdin="later news\n", now="2026-10-26T16:00:00Z")
        self.assertEqual(r.returncode, 0, r.stderr)
        after = path.read_bytes()
        self.assertTrue(after.startswith(before))
        self.assertIn(b"## Update 2026-10-26 16:00:00Z", after)
        self.assertIn(b"later news", after)

    def test_append_without_handover_refuses(self):
        self.assertEqual(self.sd("handover", "S1", "append", stdin="x").returncode, 2)


class Doctor(BoardCase):
    def test_healthy(self):
        self.say("S1", "MGR", "STATUS", "-", "fine")
        r = self.sd("doctor")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("healthy", r.stdout)

    def test_flags_a_credential_written_by_hand(self):
        self.say("S1", "MGR", "STATUS", "-", "fine")
        p = self.board / "chat" / "2026-10-26.md"
        with p.open("a") as f:
            f.write("12:00:01Z | S1 -> MGR | STATUS | - | password=hunter2hunter2\n")
        r = self.sd("doctor")
        self.assertEqual(r.returncode, 1)
        self.assertIn("credential", r.stdout)


def _writer(args):
    board, who, n = args
    os.environ["SWARMDESK_NOW"] = "2026-10-26T12:00:00Z"
    for i in range(n):
        swarmdesk.say(swarmdesk.load_board(Path(board)), who, "MGR", "STATUS", "-", f"{who} line {i:03d}")


class Concurrency(BoardCase):
    roster = "MGR:manager:x," + ",".join(f"W{i}:worker:x" for i in range(8))

    def test_eight_writers_lose_and_tear_nothing(self):
        with multiprocessing.get_context("spawn").Pool(8) as pool:
            pool.map(_writer, [(str(self.board), f"W{i}", 200) for i in range(8)])
        lines = self.chat_lines()
        self.assertEqual(len(lines), 1600)
        for line in lines:
            self.assertRegex(line, r"^12:00:00Z \| W\d -> MGR \| STATUS \| - \| W\d line \d{3}$")
        for i in range(8):
            mine = [l for l in lines if f"| W{i} line" in l]
            self.assertEqual(len(mine), 200)


if __name__ == "__main__":
    unittest.main()
