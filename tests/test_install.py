from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class InstallTest(unittest.TestCase):
    def test_installer_migrates_legacy_links_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            projects = home / "Projects" / "IlyasYOY"
            legacy = projects / "dotfiles"
            codex_home = home / ".codex"
            config_home = home / ".config"

            legacy_codex = legacy / "config" / "codex"
            legacy_opencode = legacy / "config" / "opencode"
            legacy_codex.mkdir(parents=True)
            legacy_opencode.mkdir(parents=True)
            codex_home.mkdir(parents=True)
            (config_home / "opencode").mkdir(parents=True)

            (codex_home / "AGENTS.md").symlink_to(legacy_codex / "AGENTS.md")
            (config_home / "opencode" / "commands").symlink_to(
                legacy_opencode / "commands"
            )

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
                (config_home / "opencode" / "commands").readlink(),
                REPO_ROOT / "config" / "opencode" / "commands",
            )
            self.assertEqual(
                (codex_home / "skills" / "IlyasYOY" / "git-commit").readlink(),
                REPO_ROOT / "config" / "agent" / "skills" / "git-commit",
            )
            self.assertEqual(
                (config_home / "opencode" / "skills" / "session-hardener").readlink(),
                REPO_ROOT / "config" / "opencode" / "skills" / "session-hardener",
            )


if __name__ == "__main__":
    unittest.main()
