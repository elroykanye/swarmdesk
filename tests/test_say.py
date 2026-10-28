"""say: one clock-stamped line per message, and every refusal the channel needs."""
import unittest

from helpers import BoardCase


class SayWrites(BoardCase):
    def test_line_format_and_clock(self):
        r = self.say("S1", "MGR", "ASK", "PROJ-12", "need a go for the test run", now="2026-10-26T13:05:12Z")
        self.assertEqual(r.returncode, 0, r.stderr)
        line = "13:05:12Z | S1 -> MGR | ASK | PROJ-12 | need a go for the test run"
        self.assertEqual(r.stdout.strip(), line)
        self.assertEqual(self.chat_lines(), [line])

    def test_day_file_has_header_once(self):
        self.say("S1", "MGR", "STATUS", "-", "one")
        self.say("S1", "MGR", "STATUS", "-", "two")
        text = self.chat()
        self.assertTrue(text.startswith("# swarmdesk channel, 2026-10-26 (UTC)"))
        self.assertEqual(text.count("# swarmdesk channel"), 1)

    def test_lines_go_to_the_utc_day_of_the_clock(self):
        self.say("S1", "MGR", "STATUS", "-", "late", now="2026-10-26T23:59:59Z")
        self.say("S1", "MGR", "STATUS", "-", "early", now="2026-10-27T00:00:01Z")
        self.assertEqual(len(self.chat_lines("2026-10-26")), 1)
        self.assertEqual(len(self.chat_lines("2026-10-27")), 1)

    def test_pipe_in_text_is_replaced(self):
        self.say("S1", "MGR", "STATUS", "-", "a | b")
        self.assertTrue(self.chat_lines()[0].endswith("| a / b"))

    def test_to_all_and_repo_ref(self):
        r = self.say("S1", "ALL", "CLAIM", "billing-api", "branch fix/x, version 1.2.4")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_manager_may_write_to_human(self):
        r = self.say("MGR", "HUMAN", "ASK", "-", "approve the schema change?")
        self.assertEqual(r.returncode, 0, r.stderr)


class SayRefuses(BoardCase):
    def assertRefused(self, r, fragment):
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn(fragment, r.stderr)
        self.assertEqual(self.chat_lines(), [])

    def test_two_recipients_on_one_line(self):
        # The lesson: "MGR -> A,B" matched neither reader, and a go-ahead sat unread for an hour.
        self.assertRefused(self.say("MGR", "S1,S2", "ANSWER", "-", "go"), "one recipient per line")
        self.assertRefused(self.say("MGR", "S1 S2", "ANSWER", "-", "go"), "one recipient per line")

    def test_unknown_ids(self):
        self.assertRefused(self.say("S9", "MGR", "STATUS", "-", "x"), "S9")
        self.assertRefused(self.say("S1", "S9", "STATUS", "-", "x"), "S9")

    def test_only_manager_writes_to_human(self):
        self.assertRefused(self.say("S1", "HUMAN", "ASK", "-", "may I?"), "only the manager")

    def test_unknown_type(self):
        self.assertRefused(self.say("S1", "MGR", "SHOUT", "-", "x"), "SHOUT")

    def test_bad_ref(self):
        self.assertRefused(self.say("S1", "MGR", "STATUS", "two words", "x"), "REF")

    def test_multi_line(self):
        self.assertRefused(self.say("S1", "MGR", "STATUS", "-", "a\nb"), "one line")
        self.assertRefused(self.say("S1", "MGR", "STATUS", "-", "a\rb"), "one line")

    def test_empty(self):
        self.assertRefused(self.say("S1", "MGR", "STATUS", "-", "   "), "empty")

    def test_length_cap(self):
        self.assertRefused(self.say("S1", "MGR", "STATUS", "-", "x" * 701), "701")
        self.assertEqual(self.say("S1", "MGR", "STATUS", "-", "x" * 700).returncode, 0)

    def test_credentials(self):
        samples = [
            "token eyJhbGciOiJIUzI1NiJ9abcdefghijklmnop",
            "Bearer abcdefghijklmnopqrstuvwxyz123",
            "password=hunter2hunter2",
            'api_key: "abcd1234efgh"',
            "ghp_abcdefghijklmnopqrstuvwx",
            "AKIAABCDEFGHIJKLMNOP",
            "sk-ant-api03-abcdefghijklmnopqrstuv",
            "-----BEGIN OPENSSH PRIVATE KEY-----",
        ]
        for s in samples:
            with self.subTest(s=s):
                self.assertRefused(self.say("S1", "MGR", "STATUS", "-", s), "credential")

    def test_placeholder_times(self):
        # The lesson: "read 14:1xZ" was written as if it were a clock reading.
        for s in ["read 14:1xZ", "done at 14:xxZ", "around 09:xx"]:
            with self.subTest(s=s):
                self.assertRefused(self.say("S1", "MGR", "STATUS", "-", s), "clock")
        self.assertEqual(self.say("S1", "MGR", "STATUS", "-", "read 14:12:05Z").returncode, 0)


if __name__ == "__main__":
    unittest.main()
