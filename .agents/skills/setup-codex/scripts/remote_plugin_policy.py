#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["tomlkit==0.13.3"]
# ///
"""Audit Codex app-server plugin state and maintain a remote-skill denylist."""

from __future__ import annotations

import argparse
import copy
import json
import select
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import Any, Iterable

import tomlkit
from tomlkit.items import AoT, Table


ALLOWED_MARKETPLACES = {"openai-bundled", "openai-primary-runtime"}
MANAGED_COMMENT = "setup-codex: managed remote-skill denylist"
DEFAULT_TIMEOUT_SECONDS = 30.0


class RemotePolicyError(RuntimeError):
    pass


def _source_is_remote(plugin: dict[str, Any]) -> bool:
    source = plugin.get("source")
    return isinstance(source, dict) and source.get("type") == "remote"


def _marketplace_path_fragment(name: str) -> str:
    return f"/{name.strip('/')}/"


def summarize_state(
    installed_response: dict[str, Any], skills_response: dict[str, Any]
) -> dict[str, Any]:
    """Return a secret-free policy view derived only from app-server responses."""
    remote_plugins: list[dict[str, Any]] = []
    remote_marketplaces: set[str] = set()
    remote_namespaces: set[str] = set()

    for marketplace in installed_response.get("marketplaces", []):
        marketplace_name = str(marketplace.get("name", ""))
        for plugin in marketplace.get("plugins", []):
            if not plugin.get("installed") or not _source_is_remote(plugin):
                continue
            plugin_id = str(plugin.get("id", ""))
            namespace = plugin_id.split("@", 1)[0]
            if not plugin_id or not namespace:
                continue
            remote_marketplaces.add(marketplace_name)
            remote_namespaces.add(namespace)
            remote_plugins.append(
                {
                    "id": plugin_id,
                    "marketplace": marketplace_name,
                    "installPolicy": plugin.get("installPolicy"),
                    "installPolicySource": plugin.get("installPolicySource"),
                }
            )

    all_skills: list[dict[str, Any]] = []
    for entry in skills_response.get("data", []):
        all_skills.extend(entry.get("skills", []))

    remote_skills: dict[str, dict[str, Any]] = {}
    allowed_skills: dict[str, dict[str, Any]] = {}
    for skill in all_skills:
        name = str(skill.get("name", ""))
        path = str(skill.get("path", "")).replace("\\", "/")
        namespace = name.split(":", 1)[0]
        is_allowed = any(
            _marketplace_path_fragment(marketplace) in path
            for marketplace in ALLOWED_MARKETPLACES
        )
        is_remote = (
            namespace in remote_namespaces
            or any(
                _marketplace_path_fragment(marketplace) in path
                for marketplace in remote_marketplaces
            )
            or (
                "/plugins/cache/" in path
                and "-remote/" in path
                and not is_allowed
            )
        )
        summary = {"name": name, "enabled": bool(skill.get("enabled"))}
        if name and is_remote and not is_allowed:
            remote_skills[name] = summary
        elif name and is_allowed:
            allowed_skills[name] = summary

    return {
        "remotePlugins": sorted(remote_plugins, key=lambda item: item["id"].casefold()),
        "remoteSkills": sorted(remote_skills.values(), key=lambda item: item["name"].casefold()),
        "allowedSkills": sorted(allowed_skills.values(), key=lambda item: item["name"].casefold()),
        "marketplaceLoadErrors": installed_response.get("marketplaceLoadErrors", []),
    }


def _is_managed(table: Table) -> bool:
    return MANAGED_COMMENT in table.as_string()


def _managed_entry(name: str, existing: Table | None = None) -> Table:
    table = copy.deepcopy(existing) if existing is not None else tomlkit.table()
    if not _is_managed(table):
        table.add(tomlkit.comment(MANAGED_COMMENT))
    table["name"] = name
    table["enabled"] = False
    return table


def sync_denylist_text(
    source: str,
    remote_skill_names: Iterable[str],
    allowed_skill_names: Iterable[str],
) -> tuple[str, list[str]]:
    """Merge exact remote skill names into a comment-marked denylist."""
    try:
        document = tomlkit.parse(source)
        before = tomllib.loads(source)
    except Exception as exc:
        raise RemotePolicyError(f"invalid TOML: {exc}") from exc

    skills = document.get("skills")
    if skills is None:
        skills = tomlkit.table()
        document.add("skills", skills)
    if not isinstance(skills, Table):
        raise RemotePolicyError("skills must be a TOML table")

    configs = skills.get("config")
    if configs is None:
        configs = tomlkit.aot()
    if not isinstance(configs, AoT):
        raise RemotePolicyError(
            "skills.config must use [[skills.config]] tables; refusing a lossy rewrite"
        )

    allowed = set(allowed_skill_names)
    remote = set(remote_skill_names) - allowed
    unrelated: list[Table] = []
    managed: dict[str, Table] = {}
    metadata_changed = False

    for item in configs:
        if not isinstance(item, Table):
            raise RemotePolicyError("skills.config contains a non-table entry")
        name_value = item.get("name")
        name = str(name_value) if name_value is not None else ""
        marked = _is_managed(item)
        if marked and name in allowed:
            metadata_changed = True
            continue
        if marked or name in remote:
            if not name:
                raise RemotePolicyError("managed skills.config entry has no name")
            if not marked:
                metadata_changed = True
            managed.setdefault(name, _managed_entry(name, item))
        else:
            unrelated.append(item)

    added: list[str] = []
    for name in sorted(remote, key=str.casefold):
        if name not in managed:
            managed[name] = _managed_entry(name)
            added.append(name)

    replacement = tomlkit.aot()
    for item in unrelated:
        replacement.append(item)
    for name in sorted(managed, key=str.casefold):
        replacement.append(managed[name])
    skills["config"] = replacement

    candidate = tomlkit.dumps(document)
    try:
        after = tomllib.loads(candidate)
    except tomllib.TOMLDecodeError as exc:
        raise RemotePolicyError(f"denylist writer produced invalid TOML: {exc}") from exc

    expected = copy.deepcopy(before)
    expected_skills = expected.setdefault("skills", {})
    expected_skills["config"] = after["skills"]["config"]
    if after != expected:
        raise RemotePolicyError("denylist sync changed data outside skills.config")
    if after == before and not metadata_changed:
        return source, added
    return candidate, added


class AppServerClient:
    def __init__(
        self,
        codex_bin: str,
        *,
        config_overrides: Iterable[str] = (),
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        command = [codex_bin]
        for override in config_overrides:
            command.extend(["-c", override])
        command.extend(["app-server", "--stdio"])
        self.timeout = timeout
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._next_id = 1
        self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "setup-codex-remote-policy",
                    "title": "Setup Codex remote policy",
                    "version": "1",
                },
                "capabilities": {
                    "experimentalApi": True,
                    "requestAttestation": False,
                },
            },
        )

    def __enter__(self) -> AppServerClient:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if self.process.stdin is None or self.process.stdout is None:
            raise RemotePolicyError("app-server pipes are unavailable")
        request_id = self._next_id
        self._next_id += 1
        payload = {"method": method, "id": request_id, "params": params}
        self.process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        self.process.stdin.flush()

        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            remaining = max(0.0, deadline - time.monotonic())
            readable, _, _ = select.select([self.process.stdout], [], [], remaining)
            if not readable:
                break
            line = self.process.stdout.readline()
            if not line:
                break
            try:
                response = json.loads(line)
            except json.JSONDecodeError:
                continue
            if response.get("id") != request_id:
                continue
            if "error" in response:
                raise RemotePolicyError(
                    f"app-server {method} failed: {response['error']}"
                )
            result = response.get("result")
            return result if isinstance(result, dict) else {}

        stderr = ""
        if self.process.poll() is not None and self.process.stderr is not None:
            stderr = self.process.stderr.read().strip()
        detail = f": {stderr}" if stderr else ""
        raise RemotePolicyError(f"app-server {method} timed out or exited{detail}")

    def close(self) -> None:
        if self.process.poll() is not None:
            return
        if self.process.stdin is not None:
            self.process.stdin.close()
        self.process.terminate()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=3)


def audit(codex_bin: str, cwd: Path, *, remote_catalog: bool) -> dict[str, Any]:
    overrides = ["features.remote_plugin=true"] if remote_catalog else []
    with AppServerClient(codex_bin, config_overrides=overrides) as client:
        installed = client.request("plugin/installed", {"cwds": [str(cwd)]})
        skills = client.request(
            "skills/list", {"cwds": [str(cwd)], "forceReload": True}
        )
    return summarize_state(installed, skills)


def verify_name_selector(codex_bin: str, cwd: Path, state: dict[str, Any]) -> str:
    probe = next(
        (
            skill["name"]
            for skill in state["allowedSkills"]
            if skill.get("enabled") is True
        ),
        None,
    )
    if probe is None:
        raise RemotePolicyError(
            "cannot verify name-based overrides: no enabled bundled/runtime skill found"
        )
    override = f"skills.config=[{{name={json.dumps(probe)},enabled=false}}]"
    with AppServerClient(
        codex_bin,
        config_overrides=["features.remote_plugin=true", override],
    ) as client:
        response = client.request(
            "skills/list", {"cwds": [str(cwd)], "forceReload": True}
        )
    skills = [
        skill
        for entry in response.get("data", [])
        for skill in entry.get("skills", [])
        if skill.get("name") == probe
    ]
    if not skills or any(skill.get("enabled") is not False for skill in skills):
        raise RemotePolicyError(
            f"current Codex does not honor name-based skill override for {probe}"
        )
    return probe


def _write_json(state: dict[str, Any]) -> None:
    print(json.dumps(state, indent=2, sort_keys=True))


def _prepare(args: argparse.Namespace) -> int:
    state = audit(args.codex_bin, args.cwd, remote_catalog=True)
    if state["marketplaceLoadErrors"]:
        raise RemotePolicyError("app-server reported marketplace load errors")
    probe = verify_name_selector(args.codex_bin, args.cwd, state)
    source = args.config.read_text()
    candidate, added = sync_denylist_text(
        source,
        (skill["name"] for skill in state["remoteSkills"]),
        (skill["name"] for skill in state["allowedSkills"]),
    )
    if args.output.resolve() == args.config.resolve():
        raise RemotePolicyError("output must not overwrite input")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(candidate)
    print(
        "remote policy: candidate written; "
        f"remote skills={len(state['remoteSkills'])}; added={len(added)}; "
        f"name selector probe={probe}"
    )
    return 0


def _uninstall(args: argparse.Namespace) -> int:
    with AppServerClient(
        args.codex_bin, config_overrides=["features.remote_plugin=true"]
    ) as client:
        installed = client.request("plugin/installed", {"cwds": [str(args.cwd)]})
        skills = client.request(
            "skills/list", {"cwds": [str(args.cwd)], "forceReload": True}
        )
        state = summarize_state(installed, skills)
        removed: list[str] = []
        skipped: list[str] = []
        failures: list[str] = []
        for plugin in state["remotePlugins"]:
            plugin_id = plugin["id"]
            if plugin.get("installPolicy") != "AVAILABLE":
                skipped.append(plugin_id)
                continue
            try:
                client.request("plugin/uninstall", {"pluginId": plugin_id})
                removed.append(plugin_id)
            except RemotePolicyError:
                failures.append(plugin_id)
    print(
        "remote uninstall: "
        f"removed={len(removed)}; default-or-managed={len(skipped)}; failures={len(failures)}"
    )
    if failures:
        print("failed plugin ids: " + ", ".join(sorted(failures)), file=sys.stderr)
        return 1
    return 0


def _verify(args: argparse.Namespace) -> int:
    state = audit(args.codex_bin, args.cwd, remote_catalog=False)
    enabled_remote = [
        skill["name"] for skill in state["remoteSkills"] if skill["enabled"]
    ]
    enabled_allowed = [
        skill["name"] for skill in state["allowedSkills"] if skill["enabled"]
    ]
    report = {
        "enabledRemoteSkills": enabled_remote,
        "enabledAllowedSkillCount": len(enabled_allowed),
        "remotePluginCount": len(state["remotePlugins"]),
        "remoteSkillCount": len(state["remoteSkills"]),
    }
    _write_json(report)
    return 1 if enabled_remote or not enabled_allowed else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit app-server remote plugins and enforce local skill isolation."
    )
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("audit")
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--config", required=True, type=Path)
    prepare.add_argument("--output", required=True, type=Path)
    subparsers.add_parser("uninstall")
    subparsers.add_parser("verify")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "audit":
            _write_json(audit(args.codex_bin, args.cwd, remote_catalog=True))
            return 0
        if args.command == "prepare":
            return _prepare(args)
        if args.command == "uninstall":
            return _uninstall(args)
        if args.command == "verify":
            return _verify(args)
        raise RemotePolicyError(f"unsupported command: {args.command}")
    except (OSError, UnicodeError, RemotePolicyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
