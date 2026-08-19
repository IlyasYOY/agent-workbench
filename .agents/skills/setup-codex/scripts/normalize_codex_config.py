#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["tomlkit==0.13.3"]
# ///
"""Normalize Codex config layout without changing its TOML data."""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path
from typing import Any, Iterable

import tomlkit
from tomlkit.container import Container
from tomlkit.items import AoT, Item, Table, Whitespace


HEADINGS = {
    "core": "Core settings",
    "safety": "Safety and execution",
    "features": "Features and memory",
    "interface": "Interface",
    "tools": "Tools and plugins",
    "projects": "Trusted projects",
    "other": "Other settings",
    "generated": "Generated application state",
}

GROUP_ORDER = tuple(HEADINGS)
GROUP_TABLES = {
    "safety": {"sandbox_workspace_write", "permissions"},
    "features": {"features", "memories", "skills"},
    "interface": {"notice", "tui"},
    "tools": {"shell_environment_policy", "plugins", "mcp_servers"},
    "projects": {"projects"},
    "generated": {"desktop", "marketplaces", "apps"},
}

ROOT_KEY_ORDER = (
    "model",
    "personality",
    "model_reasoning_effort",
    "plan_mode_reasoning_effort",
    "sandbox_mode",
    "approval_policy",
    "approvals_reviewer",
    "service_tier",
    "suppress_unstable_features_warning",
    "notify",
)

KEY_ORDER = {
    ("sandbox_workspace_write",): ("network_access", "writable_roots"),
    ("features",): (
        "plugins",
        "apps",
        "remote_plugin",
        "default_mode_request_user_input",
        "memories",
    ),
    ("memories",): (
        "generate_memories",
        "use_memories",
        "disable_on_external_context",
    ),
    ("skills",): ("config",),
    ("notice",): ("hide_rate_limit_model_nudge", "fast_default_opt_out"),
    ("tui",): (
        "notifications",
        "notification_method",
        "notification_condition",
        "status_line",
        "session_picker_view",
        "pet",
    ),
}

REPEATED_TABLES = {"plugins", "mcp_servers", "projects", "apps", "marketplaces"}
STANDARD_COMMENTS = {f"# {heading}" for heading in HEADINGS.values()}


class NormalizeError(RuntimeError):
    pass


def _key_name(key: Any) -> str:
    return key.key


def _is_standard_heading(item: Item) -> bool:
    trivia = getattr(item, "trivia", None)
    return bool(trivia and trivia.comment in STANDARD_COMMENTS)


def _take_trailing_comments(item: Item) -> list[Item]:
    if isinstance(item, AoT):
        return _take_trailing_comments(item[-1]) if item else []
    if not isinstance(item, Table):
        return []

    container = item._value
    body = list(container.body)
    end = len(body)
    comments: list[Item] = []
    while end and body[end - 1][0] is None:
        candidate = body[end - 1][1]
        if not isinstance(candidate, Whitespace) and not _is_standard_heading(candidate):
            comments.insert(0, candidate)
        end -= 1
    if end < len(body):
        _replace_body(container, body[:end])
        return comments

    for key, child in reversed(body[:end]):
        if key is not None:
            return _take_trailing_comments(child)
    return []


def _prepend_comments_to_first_child(table: Table, comments: list[Item]) -> bool:
    body = list(table._value.body)
    for key, child in body:
        if key is not None and isinstance(child, Table):
            _prepend_comments_to_table(child, comments)
            return True
        if key is not None and isinstance(child, AoT) and child:
            _prepend_comments_to_table(child[0], comments)
            return True
    return False


def _prepend_comments_to_table(table: Table, comments: list[Item]) -> None:
    body = [(None, comment) for comment in comments]
    body.extend(table._value.body)
    _replace_body(table._value, body)


def _split_entries(
    container: Container, *, promote_final: bool = False
) -> tuple[list[tuple[Any, Item, list[Item]]], list[Item]]:
    entries: list[tuple[Any, Item, list[Item]]] = []
    pending: list[Item] = []
    for key, item in container.body:
        if key is None:
            if isinstance(item, Whitespace) or _is_standard_heading(item):
                continue
            pending.append(item)
            continue
        if entries:
            pending = [*_take_trailing_comments(entries[-1][1]), *pending]
        entry_comments = pending
        if (
            entry_comments
            and isinstance(item, Table)
            and item.is_super_table()
            and _prepend_comments_to_first_child(item, entry_comments)
        ):
            entry_comments = []
        entries.append((key, item, entry_comments))
        pending = []
    if promote_final and entries:
        pending = [*_take_trailing_comments(entries[-1][1]), *pending]
    return entries, pending


def _rank(name: str, preferred: Iterable[str]) -> tuple[int, int | str]:
    preferred_tuple = tuple(preferred)
    try:
        return (0, preferred_tuple.index(name))
    except ValueError:
        return (1, name.casefold())


def _sort_table(table: Table, path: tuple[str, ...]) -> None:
    entries, trailing = _split_entries(table._value)
    preferred = KEY_ORDER.get(path, ())
    repeated = bool(path and path[-1] in REPEATED_TABLES)

    def sort_key(entry: tuple[Any, Item, list[Item]]) -> tuple[Any, ...]:
        name = _key_name(entry[0])
        item = entry[1]
        table_rank = 1 if isinstance(item, Table) else 0
        if repeated:
            return (0 if name == "_default" else 1, name.casefold())
        return (table_rank, *_rank(name, preferred))

    entries.sort(key=sort_key)
    new_body: list[tuple[Any, Item]] = []
    for key, item, comments in entries:
        if isinstance(item, Table):
            _sort_table(item, (*path, _key_name(key)))
        if comments and table.is_super_table() and isinstance(item, Table):
            _prepend_comments_to_table(item, comments)
            comments = []
        new_body.extend((None, comment) for comment in comments)
        new_body.append((key, item))
    new_body.extend((None, comment) for comment in trailing)
    _replace_body(table._value, new_body)


def _replace_body(container: Container, body: list[tuple[Any, Item]]) -> None:
    """Replace a tomlkit body and rebuild its private key index consistently."""
    container._body = body
    container._map = {
        key: index for index, (key, _item) in enumerate(body) if key is not None
    }


def _group_for(name: str, item: Item) -> str:
    if not isinstance(item, Table):
        return "core"
    for group, names in GROUP_TABLES.items():
        if name in names:
            return group
    return "other"


def normalize_text(source: str) -> str:
    try:
        document = tomlkit.parse(source)
    except Exception as exc:  # tomlkit exposes several parse exception types
        raise NormalizeError(f"invalid TOML: {exc}") from exc

    entries, trailing = _split_entries(document, promote_final=True)
    groups: dict[str, list[tuple[Any, Item, list[Item]]]] = {
        group: [] for group in GROUP_ORDER
    }
    for entry in entries:
        key, item, _comments = entry
        groups[_group_for(_key_name(key), item)].append(entry)

    for group_entries in groups.values():
        group_entries.sort(
            key=lambda entry: _rank(_key_name(entry[0]), ROOT_KEY_ORDER)
            if not isinstance(entry[1], Table)
            else (0, _key_name(entry[0]).casefold())
        )

    output = tomlkit.document()
    wrote_group = False
    for group in GROUP_ORDER:
        group_entries = groups[group]
        if not group_entries:
            continue
        if wrote_group:
            output.add(tomlkit.nl())
        output.add(tomlkit.comment(HEADINGS[group]))
        for key, item, comments in group_entries:
            if isinstance(item, Table):
                _sort_table(item, (_key_name(key),))
            for comment in comments:
                output.add(comment)
            output.add(key, item)
        wrote_group = True

    for comment in trailing:
        output.add(comment)

    normalized = tomlkit.dumps(output)
    try:
        before = tomllib.loads(source)
        after = tomllib.loads(normalized)
    except tomllib.TOMLDecodeError as exc:
        raise NormalizeError(f"normalizer produced invalid TOML: {exc}") from exc
    if before != after:
        raise NormalizeError("normalization changed TOML data")
    return normalized


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize Codex config layout without exposing values."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", metavar="PATH", type=Path)
    mode.add_argument("--output", metavar="PATH", type=Path)
    parser.add_argument("input", nargs="?", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    source_path = args.check or args.input
    if source_path is None:
        print("error: INPUT is required with --output", file=sys.stderr)
        return 2
    if args.output is not None and args.input is None:
        print("error: INPUT is required with --output", file=sys.stderr)
        return 2
    if args.output is not None and args.output.resolve() == source_path.resolve():
        print("error: output must not overwrite input", file=sys.stderr)
        return 2

    try:
        source = source_path.read_text()
        normalized = normalize_text(source)
    except (OSError, UnicodeError, NormalizeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    changed = normalized != source
    if args.check is not None:
        print("layout: needs normalization" if changed else "layout: normalized")
        return 1 if changed else 0

    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(normalized)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("layout: candidate written; data unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
