"""scripts/install.py: render the skills per harness binding, record a manifest, report drift, uninstall."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INSTALL = REPO / "scripts" / "install.py"
SKILLS = sorted(p.name for p in (REPO / "skills").iterdir() if (p / "SKILL.md").exists())


def inst(*args, home=None):
    env = None
    if home is not None:
        import os
        env = dict(os.environ, HOME=str(home), USERPROFILE=str(home))
    return subprocess.run([sys.executable, str(INSTALL), *args], capture_output=True, text=True, env=env, timeout=60)


class Install(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_bindings_lists_every_harness_with_status(self):
        r = inst("bindings")
        self.assertEqual(r.returncode, 0, r.stderr)
        for b in ["claude", "codex", "gemini", "cursor", "windsurf", "copilot", "generic"]:
            self.assertIn(b, r.stdout)
        self.assertIn("unverified", r.stdout)

    def test_dry_run_writes_nothing(self):
        r = inst("install", "--target", str(self.root), "--binding", "codex", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        for s in SKILLS:
            self.assertIn(f".agents/skills/{s}/SKILL.md", r.stdout)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_dir_layout_keeps_yaml_frontmatter(self):
        self.assertEqual(inst("install", "--target", str(self.root), "--binding", "claude").returncode, 0)
        text = (self.root / ".claude/skills/swarmdesk-worker/SKILL.md").read_text()
        self.assertTrue(text.startswith("---\nname: swarmdesk-worker\ndescription: "))

    def test_flat_layout_for_cursor(self):
        self.assertEqual(inst("install", "--target", str(self.root), "--binding", "cursor").returncode, 0)
        text = (self.root / ".cursor/rules/swarmdesk-manager.mdc").read_text()
        self.assertTrue(text.startswith("---\ndescription: "))
        self.assertIn("alwaysApply: false", text)
        self.assertIn("swarmdesk-manager", (self.root / "AGENTS.md").read_text())

    def test_generic_writes_one_agents_block_however_often_installed(self):
        (self.root / "AGENTS.md").write_text("# My project\n\nOwn notes.\n")
        for _ in range(2):
            self.assertEqual(inst("install", "--target", str(self.root), "--binding", "generic").returncode, 0)
        text = (self.root / "AGENTS.md").read_text()
        self.assertEqual(text.count("<!-- swarmdesk:begin -->"), 1)
        self.assertTrue(text.startswith("# My project\n\nOwn notes.\n"))
        self.assertTrue((self.root / ".agents/swarmdesk/swarmdesk-worker/SKILL.md").exists())

    def test_status_healthy_then_drift(self):
        inst("install", "--target", str(self.root), "--binding", "codex")
        r = inst("status", "--target", str(self.root))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("healthy", r.stdout)
        f = self.root / ".agents/skills/swarmdesk-worker/SKILL.md"
        f.write_text(f.read_text() + "\nlocal edit\n")
        r = inst("status", "--target", str(self.root))
        self.assertEqual(r.returncode, 1)
        self.assertIn("edited", r.stdout)

    def test_install_refuses_to_overwrite_a_local_edit_without_force(self):
        inst("install", "--target", str(self.root), "--binding", "codex")
        f = self.root / ".agents/skills/swarmdesk-worker/SKILL.md"
        f.write_text("mine\n")
        r = inst("install", "--target", str(self.root), "--binding", "codex")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(f.read_text(), "mine\n")
        self.assertEqual(inst("install", "--target", str(self.root), "--binding", "codex", "--force").returncode, 0)
        self.assertNotEqual(f.read_text(), "mine\n")

    def test_uninstall_removes_files_and_block(self):
        (self.root / "AGENTS.md").write_text("# Mine\n")
        inst("install", "--target", str(self.root), "--binding", "generic")
        r = inst("uninstall", "--target", str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.root / ".agents/swarmdesk").exists())
        self.assertEqual((self.root / "AGENTS.md").read_text(), "# Mine\n")

    def test_user_scope_goes_to_home(self):
        home = self.root / "home"
        home.mkdir()
        r = inst("install", "--scope", "user", "--binding", "claude", home=home)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((home / ".claude/skills/swarmdesk-manager/SKILL.md").exists())
        manifest = json.loads((home / ".config/swarmdesk/install.json").read_text())
        self.assertEqual(manifest["scope"], "user")

    def test_auto_detects_harness_folders(self):
        (self.root / ".gemini").mkdir()
        r = inst("install", "--target", str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.root / ".gemini/skills/swarmdesk-worker/SKILL.md").exists())
        self.assertFalse((self.root / ".claude").exists())


if __name__ == "__main__":
    unittest.main()
