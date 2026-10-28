"""Nothing in the published tree that should not be public.

1. No credential-looking string anywhere, except the deliberate fake samples the say tests feed to the refusal.
2. Optionally, no word from a private deny-list: set SWARMDESK_DENYLIST to a file with one regex per line. The
   list stays outside the repository, since publishing it would publish the very names it protects.
"""
import os
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import swarmdesk  # noqa: E402

# Files that hold credential-shaped text on purpose: the pattern itself, and the samples it must refuse.
DELIBERATE = {"swarmdesk.py", "tests/test_say.py", "tests/test_board.py"}
SKIP_DIRS = {".git", "__pycache__"}


def tree():
    for p in REPO.rglob("*"):
        if p.is_file() and not (set(p.relative_to(REPO).parts) & SKIP_DIRS):
            try:
                yield p.relative_to(REPO).as_posix(), p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue


class Hygiene(unittest.TestCase):
    def test_no_credentials_in_the_tree(self):
        pattern = re.compile(swarmdesk.CREDENTIAL_RE, re.IGNORECASE)
        hits = [f"{rel}:{n}" for rel, text in tree()
                if rel not in DELIBERATE and not rel.endswith("/swarmdesk.py")  # board copies of the CLI
                for n, line in enumerate(text.splitlines(), 1) if pattern.search(line)]
        self.assertEqual(hits, [])

    @unittest.skipUnless(os.environ.get("SWARMDESK_DENYLIST"), "SWARMDESK_DENYLIST not set")
    def test_no_private_names(self):
        words = [w.strip() for w in Path(os.environ["SWARMDESK_DENYLIST"]).read_text().splitlines()
                 if w.strip() and not w.startswith("#")]
        pattern = re.compile("|".join(words), re.IGNORECASE)
        hits = [f"{rel}:{n}: {m.group(0)}" for rel, text in tree()
                for n, line in enumerate(text.splitlines(), 1) for m in [pattern.search(line)] if m]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
