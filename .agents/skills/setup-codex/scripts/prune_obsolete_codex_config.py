#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["tomlkit==0.13.3"]
# ///
"""Create a Codex config candidate with explicitly obsolete entries removed."""

from __future__ import annotations

import argparse
import copy
import sys
import tomllib
from pathlib import Path
from typing import Any

import tomlkit


class PruneError(RuntimeError):
    pass


def _table(value: Any) -> Any | None:
    return value if hasattr(value, "get") and hasattr(value, "__delitem__") else None


def prune_text(source: str, app_ids: list[str]) -> tuple[str, list[str]]:
    try:
        document = tomlkit.parse(source)
        expected = copy.deepcopy(tomllib.loads(source))
    except Exception as exc:
        raise PruneError(f"invalid TOML: {exc}") from exc

    removed: list[str] = []
    features = _table(document.get("features"))
    if features is not None and "js_repl" in features:
        del features["js_repl"]
        expected.get("features", {}).pop("js_repl", None)
        removed.append("features.js_repl")

    plugins = _table(document.get("plugins"))
    computer_plugin = (
        _table(plugins.get("computer-use@openai-bundled"))
        if plugins is not None
        else None
    )
    mcp_servers = _table(document.get("mcp_servers"))
    if (
        computer_plugin is not None
        and computer_plugin.get("enabled") is True
        and mcp_servers is not None
        and "computer-use" in mcp_servers
    ):
        del mcp_servers["computer-use"]
        expected.get("mcp_servers", {}).pop("computer-use", None)
        removed.append("mcp_servers.computer-use")

    apps = _table(document.get("apps"))
    for app_id in app_ids:
        if apps is not None and app_id in apps:
            del apps[app_id]
            expected.get("apps", {}).pop(app_id, None)
            removed.append(f"apps.{app_id}")

    candidate = tomlkit.dumps(document)
    try:
        actual = tomllib.loads(candidate)
    except tomllib.TOMLDecodeError as exc:
        raise PruneError(f"pruner produced invalid TOML: {exc}") from exc
    if actual != expected:
        raise PruneError("pruning changed data outside the requested paths")
    return candidate, removed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Remove known obsolete Codex config paths without printing values."
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--remove-app", action="append", default=[], metavar="ID")
    parser.add_argument("input", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.output.resolve() == args.input.resolve():
        print("error: output must not overwrite input", file=sys.stderr)
        return 2
    try:
        source = args.input.read_text()
        candidate, removed = prune_text(source, args.remove_app)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(candidate)
    except (OSError, UnicodeError, PruneError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"obsolete: candidate written; removed paths: {len(removed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
