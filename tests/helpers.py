"""Shared helpers: run the CLI as a subprocess against a throwaway board, with a pinned clock."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLI = REPO / "swarmdesk.py"

DEFAULT_ROSTER = "MGR:manager:claude-code,S1:worker:codex,S2:worker:gemini,REV:reviewer:claude-code,RUN:runner:codex"


def run(args, now=None, board=None, stdin=None, cli=CLI):
    """Run swarmdesk.py with args; returns CompletedProcess (text). `now` pins the clock (ISO, UTC)."""
    env = dict(os.environ)
    env.pop("SWARMDESK_BOARD", None)
    if now is not None:
        env["SWARMDESK_NOW"] = now
    else:
        env.pop("SWARMDESK_NOW", None)
    cmd = [sys.executable, str(cli)]
    if board is not None:
        cmd += ["--board", str(board)]
    cmd += list(args)
    return subprocess.run(cmd, input=stdin, capture_output=True, text=True, env=env, timeout=60)


class BoardCase(unittest.TestCase):
    """A fresh board per test, initialised with DEFAULT_ROSTER."""

    roster = DEFAULT_ROSTER
    now = "2026-10-26T12:00:00Z"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.board = self.root / ".swarmdesk"
        r = run(["init", "--roster", self.roster, "--human", "the owner"], now=self.now, board=self.board)
        self.assertEqual(r.returncode, 0, r.stderr)

    def tearDown(self):
        self._tmp.cleanup()

    def sd(self, *args, now=None, stdin=None):
        return run(list(args), now=now or self.now, board=self.board, stdin=stdin)

    def say(self, *args, now=None):
        return self.sd("say", *args, now=now)

    def chat(self, day="2026-10-26"):
        p = self.board / "chat" / f"{day}.md"
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def chat_lines(self, day="2026-10-26"):
        return [l for l in self.chat(day).splitlines() if l[:2].isdigit()]
