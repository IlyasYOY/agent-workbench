from __future__ import annotations

import importlib.util
import tomllib
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "remote_plugin_policy.py"
SPEC = importlib.util.spec_from_file_location("remote_plugin_policy", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def installed_response() -> dict:
    return {
        "marketplaces": [
            {
                "name": "openai-curated-remote",
                "plugins": [
                    {
                        "id": "gmail@openai-curated-remote",
                        "installed": True,
                        "source": {"type": "remote"},
                        "installPolicy": "AVAILABLE",
                        "installPolicySource": None,
                    },
                    {
                        "id": "plugin-management@openai-curated-remote",
                        "installed": True,
                        "source": {"type": "remote"},
                        "installPolicy": "INSTALLED_BY_DEFAULT",
                        "installPolicySource": "IMPLICIT_CANONICAL_APP",
                    },
                ],
            },
            {
                "name": "openai-bundled",
                "plugins": [
                    {
                        "id": "visualize@openai-bundled",
                        "installed": True,
                        "source": {"type": "local", "path": "/bundled"},
                        "installPolicy": "AVAILABLE",
                    }
                ],
            },
        ],
        "marketplaceLoadErrors": [],
    }


def skills_response(version: str = "1") -> dict:
    return {
        "data": [
            {
                "cwd": "/work",
                "skills": [
                    {
                        "name": "gmail:gmail",
                        "path": f"/plugins/cache/openai-curated-remote/gmail/{version}/skills/gmail/SKILL.md",
                        "enabled": True,
                    },
                    {
                        "name": "plugin-management:plugin-management",
                        "path": f"/plugins/cache/openai-curated-remote/plugin-management/{version}/skills/plugin-management/SKILL.md",
                        "enabled": True,
                    },
                    {
                        "name": "visualize:visualize",
                        "path": "/plugins/cache/openai-bundled/visualize/1/skills/visualize/SKILL.md",
                        "enabled": True,
                    },
                    {
                        "name": "personal-skill",
                        "path": "/home/.codex/skills/personal-skill/SKILL.md",
                        "enabled": True,
                    },
                ],
                "errors": [],
            }
        ]
    }


class RemotePluginPolicyTest(unittest.TestCase):
    def test_audit_uses_app_server_source_and_excludes_allowed_marketplaces(self) -> None:
        state = MODULE.summarize_state(installed_response(), skills_response())

        self.assertEqual(
            [plugin["id"] for plugin in state["remotePlugins"]],
            [
                "gmail@openai-curated-remote",
                "plugin-management@openai-curated-remote",
            ],
        )
        self.assertEqual(
            [skill["name"] for skill in state["remoteSkills"]],
            ["gmail:gmail", "plugin-management:plugin-management"],
        )
        self.assertEqual(
            [skill["name"] for skill in state["allowedSkills"]],
            ["visualize:visualize"],
        )

    def test_version_path_change_does_not_change_name_based_denylist(self) -> None:
        first_state = MODULE.summarize_state(installed_response(), skills_response("1"))
        second_state = MODULE.summarize_state(installed_response(), skills_response("2"))
        source = """model = "gpt-5.6-sol"

[features]
plugins = true

[[skills.config]]
name = "local-skill"
enabled = true
"""
        first, _ = MODULE.sync_denylist_text(
            source,
            (skill["name"] for skill in first_state["remoteSkills"]),
            (skill["name"] for skill in first_state["allowedSkills"]),
        )
        second, added = MODULE.sync_denylist_text(
            first,
            (skill["name"] for skill in second_state["remoteSkills"]),
            (skill["name"] for skill in second_state["allowedSkills"]),
        )

        self.assertEqual(first, second)
        self.assertEqual(added, [])

    def test_repeat_sync_adds_new_remote_and_preserves_stale_bans_and_unrelated_data(self) -> None:
        source = f"""notify = ["one", "two"]

[features]
plugins = true
apps = false

[[skills.config]]
name = "local-skill"
enabled = true

[[skills.config]]
# {MODULE.MANAGED_COMMENT}
name = "old-remote:old"
enabled = false
"""
        first, added = MODULE.sync_denylist_text(
            source,
            ["gmail:gmail"],
            ["visualize:visualize"],
        )
        second, added_second = MODULE.sync_denylist_text(
            first,
            ["gmail:gmail", "google-drive:google-drive"],
            ["visualize:visualize"],
        )
        third, _ = MODULE.sync_denylist_text(
            second,
            ["gmail:gmail", "google-drive:google-drive"],
            ["visualize:visualize"],
        )

        parsed = tomllib.loads(second)
        entries = parsed["skills"]["config"]
        by_name = {entry["name"]: entry for entry in entries}
        self.assertEqual(added, ["gmail:gmail"])
        self.assertEqual(added_second, ["google-drive:google-drive"])
        self.assertIs(by_name["local-skill"]["enabled"], True)
        self.assertIs(by_name["old-remote:old"]["enabled"], False)
        self.assertIs(by_name["gmail:gmail"]["enabled"], False)
        self.assertIs(by_name["google-drive:google-drive"]["enabled"], False)
        self.assertEqual(parsed["notify"], ["one", "two"])
        self.assertIs(parsed["features"]["plugins"], True)
        self.assertEqual(second, third)

    def test_bundled_skill_is_never_kept_in_managed_denylist(self) -> None:
        source = f"""[[skills.config]]
# {MODULE.MANAGED_COMMENT}
name = "visualize:visualize"
enabled = false

[[skills.config]]
name = "personal-skill"
enabled = false
"""
        output, _ = MODULE.sync_denylist_text(
            source,
            ["gmail:gmail", "visualize:visualize"],
            ["visualize:visualize"],
        )
        names = [entry["name"] for entry in tomllib.loads(output)["skills"]["config"]]

        self.assertNotIn("visualize:visualize", names)
        self.assertIn("personal-skill", names)
        self.assertIn("gmail:gmail", names)


if __name__ == "__main__":
    unittest.main()
