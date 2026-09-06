# Agent Instructions

- Do not make commits unless the user explicitly asks.
- Preserve existing user changes.
- Explain what changed, why, and how it was verified.
- Run `make check` before calling work complete.
- Keep installable skills under `config/codex/skills` and repository-local
  skills under `.agents/skills`. All first-party skills must use explicit-only
  invocation (`policy.allow_implicit_invocation: false` in `agents/openai.yaml`).
- Keep third-party skill updates commit-pinned and review-gated.
- Validate global configuration through the repository-local setup skill; the
  installer must not edit user-owned Codex config files.
