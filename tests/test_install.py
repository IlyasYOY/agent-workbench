from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class InstallTest(unittest.TestCase):
    def test_installer_links_all_skills_and_leaves_foreign_entries_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            projects = home / "Projects" / "IlyasYOY"
            legacy = projects / "dotfiles"
            codex_home = home / ".codex"
            config_home = home / ".config"

            legacy_codex = legacy / "config" / "codex"
            legacy_agent = legacy / "config" / "agent" / "skills"
            legacy_opencode = legacy / "config" / "opencode"
            opencode_home = config_home / "opencode"
            legacy_codex.mkdir(parents=True)
            legacy_agent.mkdir(parents=True)
            legacy_opencode.mkdir(parents=True)
            codex_home.mkdir(parents=True)
            opencode_home.mkdir(parents=True)
            (legacy_agent / "grilling").mkdir()
            (legacy_agent / "grilling" / "SKILL.md").write_text("---\nname: grilling\n---\n")

            (codex_home / "AGENTS.md").symlink_to(legacy_codex / "AGENTS.md")
            (opencode_home / "commands").symlink_to(legacy_opencode / "commands")
            (opencode_home / "opencode.json").write_text('{"theme": "system"}\n')

            namespace = codex_home / "skills" / "IlyasYOY"
            namespace.mkdir(parents=True)
            # Both valid and broken links are migrated when they point into either
            # of the old skill roots. The old directories need not still exist.
            for index, skill_name in enumerate(self._installed_skill_names()):
                if index == 0:
                    old_root = Path(os.path.realpath(REPO_ROOT / "config" / "agent" / "skills"))
                elif skill_name == "golangci-lint":
                    old_root = legacy_codex / "skills"
                else:
                    old_root = legacy_agent
                (namespace / skill_name).symlink_to(old_root / skill_name)
            (namespace / "foreign").symlink_to(root / "foreign-skill")
            (namespace / "regular-file").write_text("keep\n")

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
                Path(os.path.realpath(REPO_ROOT / "config" / "codex" / "AGENTS.md")),
            )
            self.assertEqual((opencode_home / "commands").readlink(), legacy_opencode / "commands")
            self.assertEqual((opencode_home / "opencode.json").read_text(), '{"theme": "system"}\n')
            self.assertFalse((opencode_home / "AGENTS.md").exists())
            self.assertFalse((opencode_home / "skills").exists())
            self.assertFalse((opencode_home / "plugins").exists())
            for skill_name in self._installed_skill_names():
                self.assertEqual(
                    (namespace / skill_name).readlink(),
                    Path(os.path.realpath(REPO_ROOT / "config" / "codex" / "skills" / skill_name)),
                    skill_name,
                )
            self.assertEqual((namespace / "foreign").readlink(), root / "foreign-skill")
            self.assertEqual((namespace / "regular-file").read_text(), "keep\n")

    def test_installer_preserves_user_entries_that_collide_with_skill_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            namespace = home / ".codex" / "skills" / "IlyasYOY"
            namespace.mkdir(parents=True)
            (namespace / "git-commit").write_text("user-owned\n")
            foreign_target = root / "foreign-skill"
            (namespace / "vim-slides").symlink_to(foreign_target)
            environment = os.environ.copy()
            environment.update(
                {
                    "HOME": str(home),
                    "CODEX_HOME": str(home / ".codex"),
                    "ILYASYOY_PERSONAL_PROJECTS_DIR": str(home / "Projects" / "IlyasYOY"),
                    "ILYASYOY_DOTFILES_DIR": str(home / "Projects" / "IlyasYOY" / "dotfiles"),
                    "AGENT_WORKBENCH_SKIP_EXTERNAL_SKILLS": "1",
                }
            )

            subprocess.run(
                [str(REPO_ROOT / "sh" / "install.sh")],
                cwd=REPO_ROOT,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertEqual((namespace / "git-commit").read_text(), "user-owned\n")
            self.assertEqual((namespace / "vim-slides").readlink(), foreign_target)

    def test_installer_creates_fresh_skill_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            environment = os.environ.copy()
            environment.update(
                {
                    "HOME": str(home),
                    "CODEX_HOME": str(home / ".codex"),
                    "ILYASYOY_PERSONAL_PROJECTS_DIR": str(home / "Projects" / "IlyasYOY"),
                    "ILYASYOY_DOTFILES_DIR": str(home / "Projects" / "IlyasYOY" / "dotfiles"),
                    "AGENT_WORKBENCH_SKIP_EXTERNAL_SKILLS": "1",
                }
            )

            subprocess.run(
                [str(REPO_ROOT / "sh" / "install.sh")],
                cwd=REPO_ROOT,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )

            namespace = home / ".codex" / "skills" / "IlyasYOY"
            for skill_name in self._installed_skill_names():
                self.assertEqual(
                    (namespace / skill_name).readlink(),
                    (REPO_ROOT / "config" / "codex" / "skills" / skill_name).resolve(),
                )

    def test_all_owned_skills_are_explicit_only(self) -> None:
        metadata_paths = [
            REPO_ROOT / "config" / "codex" / "skills" / skill_name / "agents" / "openai.yaml"
            for skill_name in self._installed_skill_names()
        ]
        metadata_paths.append(REPO_ROOT / ".agents" / "skills" / "setup-codex" / "agents" / "openai.yaml")
        for metadata in metadata_paths:
            self.assertIn("allow_implicit_invocation: false", metadata.read_text(), metadata.as_posix())

    @staticmethod
    def _installed_skill_names() -> tuple[str, ...]:
        return (
            "git-commit",
            "golangci-lint",
            "grilling",
            "step-by-step-explanation",
            "vim-slides",
            "writing-great-skills",
        )


if __name__ == "__main__":
    unittest.main()
