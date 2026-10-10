from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
MATT_SKILLS = {
    "retro", "diagnosing-bugs", "codebase-design", "domain-modeling", "pr",
    "improve-codebase-architecture", "writing-for-agents", "handoff", "grilling",
    "grill-me", "to-questionnaire",
}
EXPLICIT_SKILLS = {
    "retro", "improve-codebase-architecture", "handoff", "grill-me", "to-questionnaire",
}


class ExternalInstallTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home"
        self.namespace = self.home / ".codex" / "skills" / "IlyasYOY"
        self.namespace.mkdir(parents=True)
        self.environment = os.environ.copy()
        self.environment.update({
            "HOME": str(self.home),
            "CODEX_HOME": str(self.home / ".codex"),
            "ILYASYOY_PERSONAL_PROJECTS_DIR": str(self.home / "Projects" / "IlyasYOY"),
            "ILYASYOY_DOTFILES_DIR": str(self.root / "legacy-dotfiles"),
            "EXTERNAL_CODEX_SKILLS_MANIFEST": str(self.root / "external-skills.conf"),
            "EXTERNAL_CODEX_SKILLS_DATA_ROOT": str(self.root / "snapshots"),
            "EXTERNAL_CODEX_SKILLS_DEST_ROOT": str(self.namespace),
            "AGENT_WORKBENCH_SKIP_EXTERNAL_SKILLS": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        })
        manifest = REPO_ROOT / "config" / "codex" / "external-skills.conf"
        rows = [line.split("|") for line in manifest.read_text().splitlines()
                if line.startswith("https://github.com/mattpocock/skills.git|")]
        self.assertEqual(len(rows), 1, "Exactly one Matt skills source is configured")
        _, tracked_ref, _, includes = rows[0]
        self.paths = includes.split(",")
        matt_repo, matt_commit = self.create_repository(
            "matt", self.paths + ["skills/engineering/tdd", "skills/productivity/teach"]
        )
        lottie_repo, lottie_commit = self.create_repository(
            "lottie", ["skills/text-to-lottie"]
        )
        (self.root / "external-skills.conf").write_text(
            f"{lottie_repo}|main|{lottie_commit}|skills/text-to-lottie\n"
            f"{matt_repo}|{tracked_ref}|{matt_commit}|{includes}\n"
        )
        self.matt_repo = matt_repo

    def create_repository(self, name: str, paths: list[str]) -> tuple[Path, str]:
        repo = self.root / name
        repo.mkdir()
        for path in paths:
            skill = repo / path
            skill_name = skill.name
            (skill / "references").mkdir(parents=True)
            (skill / "references" / "guide.md").write_text(f"Guide for {skill_name}\n")
            (skill / "SKILL.md").write_text(
                f"---\nname: {skill_name}\ndescription: Fixture skill\n---\n"
                "Read [guide](references/guide.md).\n"
            )
            (skill / "agents").mkdir()
            policy = "policy:\n  allow_implicit_invocation: false\n" if skill_name in EXPLICIT_SKILLS else ""
            (skill / "agents" / "openai.yaml").write_text(
                f'interface:\n  display_name: "{skill_name}"\n{policy}'
            )

        def git(*arguments: str) -> str:
            return subprocess.run(
                ["git", "-C", str(repo), *arguments], env=self.environment,
                check=True, capture_output=True, text=True,
            ).stdout.strip()

        git("init", "--quiet", "--initial-branch=main")
        git("add", ".")
        git("-c", "user.name=Installer Test", "-c", "user.email=test@example.invalid",
            "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Fixture skills")
        return repo, git("rev-parse", "HEAD")

    def install(self, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["make", "install"], cwd=REPO_ROOT, env=self.environment,
            check=check, capture_output=True, text=True,
        )

    def test_install_selects_all_eleven_skills_and_preserves_resources_and_user_files(self) -> None:
        foreign = self.root / "user-skill"
        (self.namespace / "foreign").symlink_to(foreign)
        (self.namespace / "user-file").write_text("keep\n")
        config = self.home / ".codex" / "config.toml"
        config.write_text('model = "user-owned"\n')
        for name in ("vim-slides", "writing-great-skills"):
            (self.namespace / name).symlink_to(REPO_ROOT / "config" / "codex" / "skills" / name)

        self.assertEqual({Path(path).name for path in self.paths}, MATT_SKILLS)
        for _ in range(2):
            self.install()
            self.assertEqual(
                {entry.name for entry in self.namespace.iterdir()},
                MATT_SKILLS | {"step-by-step-explanation", "text-to-lottie", "foreign", "user-file"},
            )
            for path in self.paths:
                installed = self.namespace / Path(path).name
                self.assertTrue(installed.is_symlink())
                for resource in ("SKILL.md", "references/guide.md", "agents/openai.yaml"):
                    self.assertEqual(
                        (installed / resource).read_bytes(),
                        (self.matt_repo / path / resource).read_bytes(),
                    )
            self.assertTrue((self.namespace / "text-to-lottie" / "SKILL.md").is_file())
            self.assertEqual((self.namespace / "foreign").readlink(), foreign)
            self.assertEqual((self.namespace / "user-file").read_text(), "keep\n")
            self.assertEqual(config.read_text(), 'model = "user-owned"\n')

    def test_install_rejects_external_name_collision_without_overwriting_user_file(self) -> None:
        collision = self.namespace / "pr"
        collision.write_text("user-owned\n")
        result = self.install(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("collides", result.stderr)
        self.assertEqual(collision.read_text(), "user-owned\n")


if __name__ == "__main__":
    unittest.main()
