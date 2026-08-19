from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


REFERENCE = Path(__file__).parents[1] / "references" / "config.toml"


class ReferenceConfigTest(unittest.TestCase):
    def test_plugin_feature_policy_keeps_bundled_plugins_without_apps(self) -> None:
        config = tomllib.loads(REFERENCE.read_text())

        self.assertIs(config["features"]["plugins"], True)
        self.assertIs(config["features"]["apps"], False)
        self.assertIs(config["features"]["remote_plugin"], False)

    def test_removed_and_plugin_owned_entries_are_not_reintroduced(self) -> None:
        config = tomllib.loads(REFERENCE.read_text())

        self.assertNotIn("js_repl", config["features"])
        self.assertNotIn("computer-use", config.get("mcp_servers", {}))


if __name__ == "__main__":
    unittest.main()
