from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class InstallTest(unittest.TestCase):
    def test_installer_migrates_codex_links_and_leaves_opencode_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            projects = home / "Projects" / "IlyasYOY"
            legacy = projects / "dotfiles"
            codex_home = home / ".codex"
            config_home = home / ".config"

            legacy_codex = legacy / "config" / "codex"
            legacy_opencode = legacy / "config" / "opencode"
            opencode_home = config_home / "opencode"
            legacy_codex.mkdir(parents=True)
            legacy_opencode.mkdir(parents=True)
            codex_home.mkdir(parents=True)
            opencode_home.mkdir(parents=True)

            (codex_home / "AGENTS.md").symlink_to(legacy_codex / "AGENTS.md")
            (opencode_home / "commands").symlink_to(legacy_opencode / "commands")
            (opencode_home / "opencode.json").write_text('{"theme": "system"}\n')

            environment = os.environ.copy()
            environment.update(
                {
                    "HOME": str(home),
                    "CODEX_HOME": str(codex_home),
                    "XDG_CONFIG_HOME": str(config_home),
                    "ILYASYOY_PERSONAL_PROJECTS_DIR": str(projects),
                    "ILYASYOY_DOTFILES_DIR": str(legacy),
                    "AGENT_WORKBENCH_SKIP_EXTERNAL_SKILLS": "1",
                }
            )

            for _ in range(2):
                subprocess.run(
                    [str(REPO_ROOT / "sh" / "install.sh")],
                    cwd=REPO_ROOT,
                    env=environment,
                    check=True,
                    capture_output=True,
                    text=True,
                )

            self.assertEqual(
                (codex_home / "AGENTS.md").readlink(),
                REPO_ROOT / "config" / "codex" / "AGENTS.md",
            )
            self.assertEqual(
                (opencode_home / "commands").readlink(),
                legacy_opencode / "commands",
            )
            self.assertEqual(
                (opencode_home / "opencode.json").read_text(),
                '{"theme": "system"}\n',
            )
            self.assertFalse((opencode_home / "AGENTS.md").exists())
            self.assertFalse((opencode_home / "skills").exists())
            self.assertFalse((opencode_home / "plugins").exists())
            self.assertEqual(
                (codex_home / "skills" / "IlyasYOY" / "git-commit").readlink(),
                REPO_ROOT / "config" / "agent" / "skills" / "git-commit",
            )
            self.assertEqual(
                (codex_home / "skills" / "IlyasYOY" / "vim-slides").readlink(),
                REPO_ROOT / "config" / "agent" / "skills" / "vim-slides",
            )


if __name__ == "__main__":
    unittest.main()
