from __future__ import annotations

import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1] / "scripts" / "normalize_codex_config.py"
)


class NormalizeCodexConfigTest(unittest.TestCase):
    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def normalize(self, source: str) -> str:
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.toml"
            output_path = Path(directory) / "output.toml"
            source_path.write_text(source)
            result = self.run_script("--output", str(output_path), str(source_path))
            self.assertEqual(result.returncode, 0, result.stderr)
            return output_path.read_text()

    def test_groups_sorts_and_preserves_data_comments_and_arrays(self) -> None:
        source = """# personal note
[apps.z]
enabled = false

[features]
memories = true
plugins = true

[projects.\"/z\"]
trust_level = \"trusted\"

[projects.\"/a\"]
trust_level = \"trusted\"

[mcp_servers.z]
args = [\"b\", \"a\"]
command = \"z\"

[desktop]
theme = \"dark\"

[notice]
fast_default_opt_out = true
hide_rate_limit_model_nudge = true
"""
        output = self.normalize(source)
        self.assertEqual(tomllib.loads(output), tomllib.loads(source))
        self.assertIn("# personal note", output)
        self.assertIn('args = ["b", "a"]', output)
        self.assertLess(output.index("# Features and memory"), output.index("# Interface"))
        self.assertLess(output.index("# Tools and plugins"), output.index("# Trusted projects"))
        self.assertLess(output.index('[projects."/a"]'), output.index('[projects."/z"]'))
        self.assertLess(output.index("# Trusted projects"), output.index("# Generated application state"))

    def test_default_repeated_table_is_first_and_nested_tables_stay_adjacent(self) -> None:
        source = """[apps.z]
enabled = false
[apps._default]
[desktop]
value = true
[desktop.child.deep]
answer = 42
"""
        output = self.normalize(source)
        self.assertLess(output.index("[apps._default]"), output.index("[apps.z]"))
        self.assertLess(output.index("[desktop]"), output.index("[desktop.child.deep]"))

    def test_reindexes_deep_tables_after_sorting(self) -> None:
        source = """[desktop]
z = true
a = false
[desktop.theme.fonts]
family = "mono"
[mcp_servers.node_repl]
command = "node"
[mcp_servers.node_repl.env]
Z = "last"
A = "first"
"""
        output = self.normalize(source)
        self.assertEqual(tomllib.loads(output), tomllib.loads(source))
        self.assertIn("[desktop.theme.fonts]", output)
        self.assertIn("[mcp_servers.node_repl.env]", output)

    def test_standalone_comments_follow_the_next_table_and_trailing_stays_last(self) -> None:
        source = """[sandbox_workspace_write]
network_access = false
# feature note
[features]
plugins = true # inline feature note
# plugin note
[plugins.zeta]
enabled = true
# mcp note
[mcp_servers.alpha]
command = "alpha"
# desktop note
[desktop]
theme = "dark"
# trailing note
"""
        output = self.normalize(source)
        self.assertLess(output.index("# feature note"), output.index("[features]"))
        self.assertLess(output.index("[plugins.zeta]"), output.index("# plugin note"))
        self.assertLess(output.index("[mcp_servers.alpha]"), output.index("# mcp note"))
        self.assertLess(output.index("# desktop note"), output.index("[desktop]"))
        self.assertIn("plugins = true # inline feature note", output)
        self.assertTrue(output.rstrip().endswith("# trailing note"))

    def test_comment_before_first_implicit_child_follows_that_child_when_sorted(self) -> None:
        source = """# zeta app note
[apps.zeta]
enabled = true
# alpha app note
[apps.alpha]
enabled = false
# zeta plugin note
[plugins.zeta]
enabled = true
# alpha plugin note
[plugins.alpha]
enabled = false
# zeta project note
[projects.\"/zeta\"]
trust_level = "trusted"
# alpha project note
[projects.\"/alpha\"]
trust_level = "trusted"
"""
        output = self.normalize(source)
        self.assertNotIn("\n[apps]\n", output)
        self.assertNotIn("\n[plugins]\n", output)
        self.assertNotIn("\n[projects]\n", output)
        self.assertLess(output.index("[apps.alpha]"), output.index("# zeta app note"))
        self.assertLess(output.index("[apps.zeta]"), output.index("# zeta app note"))
        self.assertLess(output.index("[plugins.alpha]"), output.index("# zeta plugin note"))
        self.assertLess(output.index("[plugins.zeta]"), output.index("# zeta plugin note"))
        self.assertLess(output.index('[projects."/alpha"]'), output.index("# zeta project note"))
        self.assertLess(output.index('[projects."/zeta"]'), output.index("# zeta project note"))

    def test_is_idempotent_and_does_not_duplicate_headings(self) -> None:
        source = """# Interface
[tui]
pet = \"disabled\"
notifications = true
"""
        once = self.normalize(source)
        twice = self.normalize(once)
        self.assertEqual(once, twice)
        self.assertEqual(once.count("# Interface"), 1)

    def test_skills_table_is_grouped_with_features_without_reordering_config(self) -> None:
        source = """[notice]
fast_default_opt_out = true

[[skills.config]]
name = "zeta:skill"
enabled = false

[[skills.config]]
name = "alpha:skill"
enabled = false

[features]
plugins = true
"""
        output = self.normalize(source)
        twice = self.normalize(output)
        parsed = tomllib.loads(output)

        self.assertLess(output.index("[features]"), output.index("[[skills.config]]"))
        self.assertLess(output.index("[[skills.config]]"), output.index("# Interface"))
        self.assertEqual(
            [entry["name"] for entry in parsed["skills"]["config"]],
            ["zeta:skill", "alpha:skill"],
        )
        self.assertEqual(output, twice)
        self.assertEqual(output.count("# Interface"), 1)

    def test_check_modes_and_no_value_leak(self) -> None:
        source = '[mcp_servers.private]\ncommand = "super-secret-value"\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(source)
            result = self.run_script("--check", str(path))
            self.assertEqual(result.returncode, 1)
            self.assertNotIn("super-secret-value", result.stdout + result.stderr)
            normalized = self.normalize(source)
            path.write_text(normalized)
            result = self.run_script("--check", str(path))
            self.assertEqual(result.returncode, 0)

    def test_invalid_toml_and_same_output_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text("[broken\n")
            result = self.run_script("--check", str(path))
            self.assertEqual(result.returncode, 2)
            result = self.run_script("--output", str(path), str(path))
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
