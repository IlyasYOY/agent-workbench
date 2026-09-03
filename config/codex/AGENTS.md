# Codex Personal Instructions

I'm IlyasYOY (Ilya Ilyinykh, Илья Ильиных), I'm your prompter: 

- I speak Russian & English;
- my values: software quality, explicitness, strictness, not overly complex things;
- neovim, Go, TDD practitioner;
- have kydavoiti blog in russian.

## Instructions

Interactions: 

- Do not make commits unless the user explicitly asks for one.
- Explain what changed, why it changed, and how it was verified.
- Prefer documented Makefile/package targets over ad hoc commands. If a check was not run, say so explicitly.
- Sandbox and Approvals. Do not first try known boundary-crossing commands inside the sandbox. Request approval before the first attempt when a command is expected to need network access, browser, git, Codex config writes, or writes to protected Codex directories.

Python: 

- Must use `uv` for Python scripts and ad-hoc Python dependencies instead of installing packages into the Homebrew/system Python.
- For one-off dependencies, use: `uv run --with <package> python <script.py>`

## Personal Projects

Canonical personal repositories:

- `~/Projects/IlyasYOY/dotfiles` shell config, workstation bootstrap, Homebrew manifests, terminal or desktop config.
- `~/Projects/IlyasYOY/nvim-workbench` neovim configuration, snippets, personal plugin registration, or Neovim runtime checks, treat the target as the nvim-workbench repo unless the prompt names another path.
- `~/Projects/IlyasYOY/agent-workbench` Codex config references, custom skills, commands, plugins, or personal agent instructions, treat the target as the agent-workbench repo unless the prompt names another path.
- `~/Projects/kb-store` local storage for any project to create, edit, search, reorganize, summarize, save, capture, or persist notes, treat the target as the kb-store repo unless the prompt names another path.
