# agent-workbench

Personal Codex instructions, skills, rules, and configuration-review workflows.

The repository follows `main`. Third-party Codex skills remain pinned to exact
commits and require an explicit interactive diff review before their accepted
pin is updated.

## Install

```bash
make install
```

Installation links managed instructions, rules, and skills into `~/.codex`. It
does not edit `~/.codex/config.toml`.

Use the repository-local `$setup-codex` skill for that user-owned file.

## Update

```bash
make update
```

The update follows the checkout's configured upstream branch and repairs
first-party managed links. It does not check, install, or repair third-party
skills.

## Update third-party skills

```bash
make update-skills
```

The command reports whether each configured third-party skill repository is
current. When an update is available, it shows the diff for the selected skills
and asks whether to apply that repository's update.

## Check

```bash
make check
```

The canonical check runs ShellCheck, Python tests, reference-schema checks, and
an isolated idempotent installer test.

## Release

Run the manual **Release** workflow from the repository's default branch and
choose `patch`, `minor`, or `major`. The workflow runs the canonical check,
creates an annotated `vX.Y.Z` tag, and publishes a GitHub Release with generated
notes.

Versions live only in Git tags and GitHub Releases. With no existing release,
the first patch, minor, and major choices produce `v0.0.1`, `v0.1.0`, and
`v1.0.0`, respectively. The workflow refuses to release the same commit twice.
