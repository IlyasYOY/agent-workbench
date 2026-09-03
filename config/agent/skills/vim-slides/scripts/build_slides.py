#!/usr/bin/env python3
"""Assemble recursively ordered Markdown slides into one shareable document."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Callable


LABEL = r"[A-Za-z0-9][A-Za-z0-9_-]*"
DEFINITION_RE = re.compile(rf"^(?P<indent> {{0,3}})\[(?P<footnote>\^?)(?P<label>{LABEL})\](?P<colon>:\s*)")
FENCE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")
CONTINUATION_RE = re.compile(r"^[ \t]+")
FOOTNOTE_RE = re.compile(rf"\[\^(?P<label>{LABEL})\]")
FULL_REFERENCE_RE = re.compile(rf"(?P<text>!?\[[^\]\n]*\])\[(?P<label>{LABEL})\]")
COLLAPSED_REFERENCE_RE = re.compile(rf"(?P<image>!?)\[(?P<label>{LABEL})\]\[\]")
SHORTCUT_REFERENCE_RE = re.compile(rf"(?<!!)\[(?P<label>{LABEL})\](?!\s*:|[\[(])")


class BuildError(RuntimeError):
    """Raised when source slides cannot be assembled safely."""


@dataclass(frozen=True)
class Definitions:
    references: dict[str, str]
    footnotes: dict[str, str]


@dataclass(frozen=True)
class Definition:
    kind: str
    label: str
    key: str
    start: int
    end: int
    body: str


@dataclass(frozen=True)
class Slide:
    relative_path: Path
    lines: list[str]
    ignored: list[bool]
    definitions: list[Definition]


def fenced_lines(lines: list[str]) -> list[bool]:
    flags: list[bool] = []
    active_character: str | None = None
    active_length = 0
    for line in lines:
        match = FENCE_RE.match(line)
        if active_character is None:
            flags.append(False)
            if match:
                fence = match.group("fence")
                active_character = fence[0]
                active_length = len(fence)
            continue

        flags.append(True)
        if match:
            fence = match.group("fence")
            if fence[0] == active_character and len(fence) >= active_length:
                active_character = None
                active_length = 0
    return flags


def definition_end(lines: list[str], ignored: list[bool], start: int) -> int:
    end = start + 1
    while end < len(lines):
        if ignored[end] or DEFINITION_RE.match(lines[end]):
            break
        if CONTINUATION_RE.match(lines[end]):
            end += 1
            continue
        if lines[end].strip():
            break

        probe = end + 1
        while probe < len(lines) and not lines[probe].strip():
            probe += 1
        if probe < len(lines) and not ignored[probe] and CONTINUATION_RE.match(lines[probe]):
            end += 1
            continue
        break
    return end


def parse_slide(relative_path: Path, text: str) -> Slide:
    lines = text.splitlines(keepends=True)
    ignored = fenced_lines(lines)
    definitions: list[Definition] = []
    seen: set[tuple[str, str]] = set()
    index = 0
    while index < len(lines):
        if ignored[index]:
            index += 1
            continue
        match = DEFINITION_RE.match(lines[index])
        if not match:
            index += 1
            continue

        label = match.group("label")
        kind = "footnote" if match.group("footnote") else "reference"
        if label.isdigit():
            raise BuildError(
                f"numeric {kind} label {label!r} in {relative_path.as_posix()}; "
                "use a descriptive name"
            )
        key = label.casefold()
        identity = (kind, key)
        if identity in seen:
            raise BuildError(f"duplicate {kind} label {label!r} in {relative_path.as_posix()}")
        seen.add(identity)

        end = definition_end(lines, ignored, index)
        content = [lines[index][match.end() :], *lines[index + 1 : end]]
        normalized = [line.rstrip(" \t\r\n") for line in content]
        while normalized and not normalized[-1]:
            normalized.pop()
        definitions.append(
            Definition(
                kind=kind,
                label=label,
                key=key,
                start=index,
                end=end,
                body="\n".join(normalized),
            )
        )
        index = end

    return Slide(
        relative_path=relative_path,
        lines=lines,
        ignored=ignored,
        definitions=definitions,
    )


def allocate_label(base: str, used: set[str], next_number: dict[str, int]) -> str:
    key = base.casefold()
    number = next_number.get(key, 1)
    while f"{base}-{number}".casefold() in used:
        number += 1
    next_number[key] = number + 1
    label = f"{base}-{number}"
    used.add(label.casefold())
    return label


def plan_labels(
    slides: list[Slide],
) -> tuple[dict[tuple[int, str, str], str], set[tuple[int, int]]]:
    occurrences: dict[tuple[str, str], list[tuple[int, Definition]]] = {}
    used = {"reference": set(), "footnote": set()}
    for slide_index, slide in enumerate(slides):
        for definition in slide.definitions:
            occurrences.setdefault((definition.kind, definition.key), []).append(
                (slide_index, definition)
            )
            used[definition.kind].add(definition.key)

    assignments: dict[tuple[int, str, str], str] = {}
    kept: set[tuple[int, int]] = set()
    next_number = {"reference": {}, "footnote": {}}
    for (kind, key), definitions in occurrences.items():
        groups: dict[str, list[tuple[int, Definition]]] = {}
        for occurrence in definitions:
            groups.setdefault(occurrence[1].body, []).append(occurrence)

        if len(groups) == 1:
            labels = [definitions[0][1].label]
        else:
            base = definitions[0][1].label
            labels = [
                allocate_label(base, used[kind], next_number[kind])
                for _ in groups
            ]

        for output_label, group in zip(labels, groups.values(), strict=True):
            kept.add((group[0][0], group[0][1].start))
            for slide_index, definition in group:
                assignments[(slide_index, kind, key)] = output_label

    return assignments, kept


def rewrite_outside_inline_code(text: str, rewrite: Callable[[str], str]) -> str:
    result: list[str] = []
    cursor = 0
    while cursor < len(text):
        opening = text.find("`", cursor)
        if opening == -1:
            result.append(rewrite(text[cursor:]))
            break
        result.append(rewrite(text[cursor:opening]))
        run_end = opening
        while run_end < len(text) and text[run_end] == "`":
            run_end += 1
        marker = text[opening:run_end]
        closing = text.find(marker, run_end)
        if closing == -1:
            result.append(text[opening:])
            break
        closing_end = closing + len(marker)
        result.append(text[opening:closing_end])
        cursor = closing_end
    return "".join(result)


def rewrite_segment(segment: str, definitions: Definitions) -> str:
    def replace_definition(match: re.Match[str]) -> str:
        source = definitions.footnotes if match.group("footnote") else definitions.references
        replacement = source.get(match.group("label").casefold())
        if replacement is None:
            return match.group(0)
        marker = "^" if match.group("footnote") else ""
        return f"{match.group('indent')}[{marker}{replacement}]{match.group('colon')}"

    def replace_footnote(match: re.Match[str]) -> str:
        replacement = definitions.footnotes.get(match.group("label").casefold())
        return f"[^{replacement}]" if replacement else match.group(0)

    def replace_full_reference(match: re.Match[str]) -> str:
        replacement = definitions.references.get(match.group("label").casefold())
        return f"{match.group('text')}[{replacement}]" if replacement else match.group(0)

    def replace_collapsed_reference(match: re.Match[str]) -> str:
        replacement = definitions.references.get(match.group("label").casefold())
        return f"{match.group('image')}[{replacement}][]" if replacement else match.group(0)

    def replace_shortcut_reference(match: re.Match[str]) -> str:
        replacement = definitions.references.get(match.group("label").casefold())
        return f"[{replacement}]" if replacement else match.group(0)

    segment = DEFINITION_RE.sub(replace_definition, segment)
    segment = FOOTNOTE_RE.sub(replace_footnote, segment)
    segment = FULL_REFERENCE_RE.sub(replace_full_reference, segment)
    segment = COLLAPSED_REFERENCE_RE.sub(replace_collapsed_reference, segment)
    return SHORTCUT_REFERENCE_RE.sub(replace_shortcut_reference, segment)


def rewrite_slide(
    slide: Slide,
    slide_index: int,
    assignments: dict[tuple[int, str, str], str],
    kept: set[tuple[int, int]],
) -> str:
    references: dict[str, str] = {}
    footnotes: dict[str, str] = {}
    dropped_lines: set[int] = set()
    for definition in slide.definitions:
        output_label = assignments[(slide_index, definition.kind, definition.key)]
        destination = footnotes if definition.kind == "footnote" else references
        destination[definition.key] = output_label
        if (slide_index, definition.start) not in kept:
            dropped_lines.update(range(definition.start, definition.end))

    definitions = Definitions(references=references, footnotes=footnotes)
    rewritten: list[str] = []
    for line_index, (line, is_ignored) in enumerate(
        zip(slide.lines, slide.ignored, strict=True)
    ):
        if line_index in dropped_lines:
            continue
        if is_ignored or FENCE_RE.match(line):
            rewritten.append(line)
        else:
            rewritten.append(
                rewrite_outside_inline_code(
                    line,
                    lambda segment: rewrite_segment(segment, definitions),
                )
            )
    return "".join(rewritten).rstrip()


def discover_slides(slides_dir: Path) -> list[Path]:
    if not slides_dir.is_dir():
        raise BuildError(f"slides directory does not exist: {slides_dir}")
    slides = sorted(
        (path for path in slides_dir.rglob("*.md") if path.is_file()),
        key=lambda path: path.relative_to(slides_dir).as_posix(),
    )
    if not slides:
        raise BuildError(f"no Markdown slides found under {slides_dir}")
    return slides


def assemble(slides_dir: Path) -> str:
    slides: list[Slide] = []
    for slide in discover_slides(slides_dir):
        relative_path = slide.relative_to(slides_dir)
        try:
            text = slide.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise BuildError(f"slide is not valid UTF-8: {relative_path.as_posix()}") from error
        slides.append(parse_slide(relative_path, text))

    assignments, kept = plan_labels(slides)
    sections = [
        rewrite_slide(slide, slide_index, assignments, kept)
        for slide_index, slide in enumerate(slides)
    ]
    return "\n\n---\n\n".join(sections) + "\n"


def write_atomic(output: Path, content: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        temporary.replace(output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def build(root: Path, slides_name: Path, output_name: Path) -> Path:
    root = root.expanduser().resolve()
    slides_dir = (root / slides_name).resolve() if not slides_name.is_absolute() else slides_name.resolve()
    output = (root / output_name).resolve() if not output_name.is_absolute() else output_name.resolve()
    try:
        output.relative_to(slides_dir)
    except ValueError:
        pass
    else:
        raise BuildError("output must be outside the slides directory")
    write_atomic(output, assemble(slides_dir))
    return output


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="deck root; defaults to cwd")
    parser.add_argument("--slides-dir", type=Path, default=Path("slides"), help="slides path relative to root")
    parser.add_argument("--output", type=Path, default=Path("presentation.md"), help="output path relative to root")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        output = build(args.root, args.slides_dir, args.output)
    except (BuildError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
