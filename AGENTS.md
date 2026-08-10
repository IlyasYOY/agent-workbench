# Agent Instructions

- Do not make commits unless the user explicitly asks.
- Preserve existing user changes.
- Explain what changed, why, and how it was verified.
- Run `make check` before calling work complete.
- Keep portable skills under `config/agent` and Codex-only behavior under
  `config/codex`.
- Keep third-party skill updates commit-pinned and review-gated.
- Validate global configuration through the repository-local setup skill; the
  installer must not edit user-owned Codex config files.
