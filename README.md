# agent-workbench

Personal Codex and OpenCode instructions, skills, commands, plugins, and
configuration-review workflows.

The repository follows `main`. Third-party Codex skills remain pinned to exact
commits and require an interactive diff review before their accepted pin is
updated.

## Install

```bash
make install
```

Installation links managed instructions, rules, skills, commands, and plugins
into `~/.codex` and `~/.config/opencode`. It does not edit
`~/.codex/config.toml` or `~/.config/opencode/opencode.json`.

Use the repository-local `$setup-codex` and `$setup-opencode` skills for those
two user-owned files.

## Update

```bash
make update
```

The update follows the checkout's configured upstream branch, reviews
third-party skill changes, and repairs managed links.

## Check

```bash
make check
```

The canonical check runs ShellCheck, Python tests, reference-schema checks, and
an isolated idempotent installer test.
