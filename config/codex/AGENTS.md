# Codex Personal Instructions

I'm IlyasYOY (Ilya Ilyinykh, Илья Ильиных), your prompter.

- I speak Russian and English.
- I value software quality, explicitness, strictness, and simplicity.
- I use Neovim and Go and practice TDD.
- I have a Russian-language blog called kydavoiti.

## Instructions

Interactions:

- Do not make commits unless the user explicitly asks for one.
- Explain what changed, why it changed, and how it was verified.
- Prefer documented Makefile/package targets over ad hoc commands. If a check was not run, say so explicitly.
- Sandbox and approvals: Do not first try known boundary-crossing commands inside the sandbox. Request approval before the first attempt when a command is expected to require network access, a browser, Git, writes to Codex config files, or writes to protected Codex directories.
- If you publish a message on my behalf in a public space, such as GitHub, GitLab, or a wiki, add the following marker on a separate line at the end: "Posted by {Model Name} using Codex". (don't put in commits, there we have co-authored)

Testing:

- Prefer black-box tests through the API of a service, package, or function. That API should be sufficient to test a change in isolation.
- Verify observable behavior and contracts, not private state, implementation details, or internal call sequences. Avoid white-box tests and tests that mirror the implementation.
- If isolated testing requires reaching into internals, first reconsider the API boundaries and explicit dependencies instead of adding test-only access to private state.

Python:

- Use `uv` for Python scripts and ad hoc Python dependencies instead of installing packages into the Homebrew or system Python environment.
- For one-off dependencies, use: `uv run --with <package> python <script.py>`

## Personal Projects

Canonical personal repositories:

- `~/Projects/IlyasYOY/dotfiles`: Shell config, workstation bootstrap, Homebrew manifests, and terminal or desktop config.
- `~/Projects/IlyasYOY/nvim-workbench`: Neovim configuration, snippets, personal plugin registration, or Neovim runtime checks. Treat the nvim-workbench repo as the target unless the prompt names another path.
- `~/Projects/IlyasYOY/agent-workbench`: Codex config references, custom skills, commands, plugins, or personal agent instructions. Treat the agent-workbench repo as the target unless the prompt names another path.
- `~/Projects/kb-store`: Local storage for creating, editing, searching, reorganizing, summarizing, saving, capturing, or persisting notes for any project. Treat the kb-store repo as the target unless the prompt names another path.
