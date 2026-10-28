"""hear and watch: each reader gets its own lines once, across the UTC midnight."""
import unittest

from helpers import BoardCase


class Hear(BoardCase):
    def setUp(self):
        super().setUp()
        self.say("MGR", "S1", "ANSWER", "-", "for s1")
        self.say("MGR", "S2", "ANSWER", "-", "for s2")
        self.say("MGR", "ALL", "STATUS", "-", "for everyone")
        self.say("S1", "MGR", "STATUS", "-", "for the manager")

    def hear(self, *args, now=None):
        r = self.sd("hear", *args, now=now)
        self.assertEqual(r.returncode, 0, r.stderr)
        return [l for l in r.stdout.splitlines() if l.strip()]

    def test_reader_gets_own_and_all(self):
        self.assertEqual([l.split(" | ")[-1] for l in self.hear("S1")], ["for s1", "for everyone"])

    def test_sender_does_not_hear_lines_to_others(self):
        self.assertEqual([l.split(" | ")[-1] for l in self.hear("S2")], ["for s2", "for everyone"])

    def test_cursor_advances(self):
        self.hear("S1")
        self.assertEqual(self.hear("S1"), [])
        self.say("MGR", "S1", "ANSWER", "-", "later")
        self.assertEqual([l.split(" | ")[-1] for l in self.hear("S1")], ["later"])

    def test_cursor_is_per_reader(self):
        self.hear("S1")
        self.assertEqual(len(self.hear("S2")), 2)

    def test_peek_does_not_advance(self):
        self.assertEqual(len(self.hear("S1", "--peek")), 2)
        self.assertEqual(len(self.hear("S1")), 2)

    def test_all_is_the_managers_sweep(self):
        self.assertEqual(len(self.hear("MGR", "--all")), 4)
        self.assertEqual(self.hear("MGR", "--all"), [])

    def test_unknown_reader(self):
        r = self.sd("hear", "S9")
        self.assertEqual(r.returncode, 2)

    def test_human_reads_what_the_manager_sent(self):
        self.say("MGR", "HUMAN", "ASK", "-", "approve?")
        self.assertEqual([l.split(" | ")[-1] for l in self.hear("HUMAN")], ["approve?"])

    def test_midnight_rollover(self):
        self.hear("S1")
        self.say("MGR", "S1", "ANSWER", "-", "before midnight", now="2026-10-26T23:59:58Z")
        self.say("MGR", "S1", "ANSWER", "-", "after midnight", now="2026-10-27T00:00:02Z")
        got = [l.split(" | ")[-1] for l in self.hear("S1", now="2026-10-27T00:05:00Z")]
        self.assertEqual(got, ["before midnight", "after midnight"])

    def test_header_lines_are_never_delivered(self):
        got = self.hear("S1", "--all")
        self.assertTrue(all(l[:2].isdigit() for l in got))


class Watch(BoardCase):
    def test_watch_until_past_time_returns_after_one_pass(self):
        self.say("MGR", "S1", "ANSWER", "-", "go")
        r = self.sd("watch", "S1", "--until", "11:00Z", "--interval", "0.1", now="2026-10-26T12:00:00Z")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("| go", r.stdout)
        self.assertEqual(self.sd("hear", "S1").stdout.strip(), "")

    def test_watch_max_lines(self):
        self.say("MGR", "S1", "ANSWER", "-", "one")
        self.say("MGR", "S1", "ANSWER", "-", "two")
        r = self.sd("watch", "S1", "--max-lines", "1", "--interval", "0.1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len([l for l in r.stdout.splitlines() if l.strip()]), 1)


if __name__ == "__main__":
    unittest.main()
