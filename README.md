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

All first-party installable skills live under `config/codex/skills`.
They and the repository-local `setup-codex` skill are explicit-only: invoke them
with `$skill-name`; Codex does not automatically select them. Their
`agents/openai.yaml` files set `policy.allow_implicit_invocation: false`.

Installation migrates managed links from the former shared skills directory
and the old dotfiles layout, preserving unrelated files and links. To apply
only first-party links without processing external skills, run:

```bash
AGENT_WORKBENCH_SKIP_EXTERNAL_SKILLS=1 make install
```

If skill changes do not appear, restart Codex and use a new session.

## Managed skills

The first-party installable skill is `step-by-step-explanation`.
`vim-slides` and `writing-great-skills` are retired; installation removes their
stale managed links while preserving user-owned entries.

`config/codex/external-skills.conf` selects upstream skills at accepted commits:

- **diffusionstudio/lottie**: `text-to-lottie`.
- **mattpocock/skills — engineering**: `retro`, `diagnosing-bugs`,
  `codebase-design`, `domain-modeling`, `pr`, `improve-codebase-architecture`.
- **mattpocock/skills — productivity**: `writing-for-agents`, `handoff`,
  `grilling`, `grill-me`, `to-questionnaire`.

External skills retain their upstream content and invocation policy.
Invoke `retro`, `improve-codebase-architecture`, `handoff`, `grill-me`, and
`to-questionnaire` explicitly with `$skill-name`; the other selected Matt skills
allow automatic selection. `writing-for-agents` replaces the retired writing
reference. `pr` shapes a PR body; it does not open a pull request.

The remaining Matt skills are excluded. Installation uses the existing pinned
snapshot mechanism, without a submodule or local upstream patches. Skill
instructions do not grant additional permission to commit or publish.

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
