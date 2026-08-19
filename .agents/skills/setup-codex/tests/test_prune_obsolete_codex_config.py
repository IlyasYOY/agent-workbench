from __future__ import annotations

import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "prune_obsolete_codex_config.py"


class PruneObsoleteCodexConfigTest(unittest.TestCase):
    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_removes_obsolete_plugin_owned_and_confirmed_app_entries(self) -> None:
        source = """[features]
plugins = true
js_repl = false # removed feature
[plugins."computer-use@openai-bundled"]
enabled = true
[mcp_servers.computer-use]
command = "legacy"
[mcp_servers.node_repl]
command = "node"
[apps.external]
enabled = false
[apps.keep]
enabled = true
"""
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.toml"
            output_path = Path(directory) / "output.toml"
            source_path.write_text(source)
            result = self.run_script(
                "--output",
                str(output_path),
                "--remove-app",
                "external",
                str(source_path),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            config = tomllib.loads(output_path.read_text())
            self.assertNotIn("js_repl", config["features"])
            self.assertNotIn("computer-use", config["mcp_servers"])
            self.assertIn("node_repl", config["mcp_servers"])
            self.assertNotIn("external", config["apps"])
            self.assertIn("keep", config["apps"])

    def test_preserves_manual_computer_use_without_enabled_bundled_plugin(self) -> None:
        source = """[mcp_servers.computer-use]
command = "manual"
"""
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.toml"
            output_path = Path(directory) / "output.toml"
            source_path.write_text(source)
            result = self.run_script("--output", str(output_path), str(source_path))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("computer-use", tomllib.loads(output_path.read_text())["mcp_servers"])

    def test_rejects_invalid_toml_and_same_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text("[broken\n")
            result = self.run_script("--output", str(path), str(path))
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
