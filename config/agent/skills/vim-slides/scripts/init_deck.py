#!/usr/bin/env python3
"""Initialize a self-contained Neovim Markdown slide repository."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys


SKILL_ROOT = Path(__file__).resolve().parents[1]
DECK_ASSETS = SKILL_ROOT / "assets" / "deck"
BUILD_SCRIPT = SKILL_ROOT / "scripts" / "build_slides.py"
TITLE_TOKEN = "__VIM_SLIDES_TITLE__"


class InitError(RuntimeError):
    """Raised when a deck cannot be initialized safely."""


def initialize_deck(target: Path, title: str | None = None) -> Path:
    target = target.expanduser().resolve()
    resolved_title = (title or target.name.replace("-", " ")).strip()
    if not resolved_title or "\n" in resolved_title or "\r" in resolved_title:
        raise InitError("title must be a non-empty single line")
    if shutil.which("git") is None:
        raise InitError("git is required to initialize a slide repository")
    if target.exists() and any(target.iterdir()):
        raise InitError(f"target directory is not empty: {target}")

    target.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--quiet", str(target)], check=True)

    for source in sorted(DECK_ASSETS.rglob("*")):
        relative = source.relative_to(DECK_ASSETS)
        if relative == Path("nvim.lua"):
            relative = Path(".nvim.lua")
        destination = target / relative
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        content = source.read_text(encoding="utf-8").replace(TITLE_TOKEN, resolved_title)
        destination.write_text(content, encoding="utf-8")

    tools_dir = target / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    destination_script = tools_dir / "build-slides.py"
    shutil.copy2(BUILD_SCRIPT, destination_script)
    destination_script.chmod(destination_script.stat().st_mode | 0o111)
    return target


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a Git repository for Markdown slides presented in Neovim."
    )
    parser.add_argument("target", type=Path, help="new or empty target directory")
    parser.add_argument("--title", help="presentation title; defaults to the directory name")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        target = initialize_deck(args.target, args.title)
    except (InitError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"Initialized Vim slide deck at {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
