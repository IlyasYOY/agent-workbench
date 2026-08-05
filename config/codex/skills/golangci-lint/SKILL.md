---
name: golangci-lint
description: Manually lint and iteratively fix the current Go project with the shared GolangCI configuration.
---

# GolangCI Lint

Lint the current Go project with the shared strict configuration, distinguish
worthwhile fixes from project-inappropriate findings, and iterate until only
findings the user explicitly ignored remain.

## Constants

Use this configuration without copying or editing it:

`$HOME/Projects/IlyasYOY/nvim-workbench/config/.golangci.yml`

Use this exact tool version in every command:

```sh
# golangci-lint version: v2.12.2
go run github.com/golangci/golangci-lint/v2/cmd/golangci-lint@v2.12.2
```

Before linting, verify that the configuration exists and its
`# golangci-lint version:` comment is `v2.12.2`. Stop and report a maintenance
mismatch instead of silently changing either version.

## Workflow

1. Ground the run in the current project:
   - Read the nearest `AGENTS.md` and relevant repository instructions.
   - Inspect `git status --short` and the existing diff. Preserve user changes.
   - Work from the current Go module or workspace root. If the current project
     does not resolve to a Go module/workspace, stop and ask which module to use.

   Completion criterion: the project root, its instructions, and its existing
   dirty state are known.

2. Ask the user to choose `whole repository` or `diff`, unless they already
   chose the scope in the invocation.

   For `diff`, list local branches and remote-tracking refs, then ask the user
   for the branch/ref to compare with. Do not infer it and do not fetch. Verify
   the supplied ref resolves to a local commit and compute its merge base with
   `HEAD`. Include committed, staged, unstaged, and untracked files changed
   since that merge base.

   Completion criterion: either whole-repository scope or one validated local
   base ref and merge base is recorded.

3. Before the first `go run`, request approval for network access because Go
   can contact its module proxy even when module sources are cached. Run the
   diagnostic command without `--fix`:

   ```sh
   # Whole repository
   go run github.com/golangci/golangci-lint/v2/cmd/golangci-lint@v2.12.2 run \
     --config "$HOME/Projects/IlyasYOY/nvim-workbench/config/.golangci.yml" \
     ./...

   # Diff against the selected local ref
   go run github.com/golangci/golangci-lint/v2/cmd/golangci-lint@v2.12.2 run \
     --config "$HOME/Projects/IlyasYOY/nvim-workbench/config/.golangci.yml" \
     --new-from-merge-base "<base-ref>" \
     ./...
   ```

   Treat compilation, configuration, dependency, and tool failures as blockers,
   not lint findings. Diagnose them without changing project code.

   Completion criterion: a complete lint result exists for the selected scope.

4. Triage every finding before editing:
   - Recommend fixes for correctness, security, performance, maintainability,
     formatting, or clear Go idioms that fit repository conventions.
   - Separate opinionated findings caused by applying a shared configuration to
     a project with different conventions.
   - Treat `nolintlint` findings and any addition, removal, or rewrite of a
     `//nolint` directive as config-sensitive. Recommend changing them only when
     the suppression is objectively invalid and the project conventions support
     the change.
   - Present a concise grouped report, recommend what to fix or ignore, and ask
     once for confirmation plus any findings to ignore.

   Keep confirmed ignores in a session-only ledger identified by linter,
   file/symbol, and finding. Never persist ignores in either lint configuration.

   Completion criterion: the actionable set and ignore ledger are explicit.

5. Fix the confirmed actionable set in small batches. Choose the safest useful
   method for each batch:
   - Edit manually for semantic or precise changes.
   - Use the same `run` command with `--fix` for supported automatic fixes.
   - Use the pinned `fmt` command for the configured `gofumpt`, `goimports`, and
     `golines` formatters.

   Preview formatting before rewriting:

   ```sh
   go run github.com/golangci/golangci-lint/v2/cmd/golangci-lint@v2.12.2 fmt \
     --config "$HOME/Projects/IlyasYOY/nvim-workbench/config/.golangci.yml" \
     --diff
   ```

   In diff mode, apply `fmt` only when every file in its preview already belongs
   to the selected merge-base diff. Otherwise use scoped/manual fixes or ask the
   user before expanding scope. Do not use `fmt` or `--fix` when it could rewrite
   an ignored finding or unrelated dirty work.

   Record the pre-command status/diff, inspect the resulting diff after every
   automatic rewrite, and stop if it touched anything outside the confirmed
   scope. Never stage or commit.

   Completion criterion: the batch changes only confirmed findings and preserves
   unrelated work.

6. Rerun the identical diagnostic command after every batch. Run focused tests
   for behavioral changes and the repository's canonical check before declaring
   success. Repeat triage, fixing, and verification for newly exposed findings;
   do not ask for confirmation again unless a new ambiguous category appears.

   Completion criterion: the diagnostic command reports no findings, or every
   remaining finding matches the ignore ledger. If ignored findings keep the
   command nonzero, report that expected status and list them exactly.

## Final Report

Report:

- selected scope and base ref when applicable
- issues fixed, grouped by linter or intent
- explicitly ignored findings and why they remain
- automatic `fmt` or `--fix` commands used
- lint, test, and canonical-check results
- any command not run or verification gap
