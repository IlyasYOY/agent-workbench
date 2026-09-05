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
- If you publish a message on my behalf in a public space, such as GitHub, GitLab, or a wiki, add the following marker on a separate line at the end: "Posted on behalf of IlyasYOY by {Model Name} using Codex".

Python:

- Use `uv` for Python scripts and ad hoc Python dependencies instead of installing packages into the Homebrew or system Python environment.
- For one-off dependencies, use: `uv run --with <package> python <script.py>`

## Subagents

Use subagents proactively when the task contains two or more independent,
bounded workstreams that can run in parallel.

Prefer delegation for:

- Codebase exploration and research.
- Independent implementation areas.
- Running and analyzing tests.
- Code review and verification.

Run independent work in parallel when it improves speed or quality.
Avoid subagents for trivial tasks or when coordination would cost more than
doing the work directly.

Avoid multiple agents editing overlapping files concurrently.
Wait for delegated work and integrate the results before finishing.

### Model and reasoning selection

For each subagent, explicitly choose an available model and supported reasoning
effort suited to the task instead of automatically inheriting the parent settings.
Prefer the least costly option that can reliably meet the required quality.

Use low reasoning for straightforward tasks, medium for multi-step work, and high
or above when complexity or risk warrants it. Escalate the model or reasoning
effort if results are insufficient. Use the current tool's available model IDs
and supported settings; these examples apply only when available.

## Personal Projects

Canonical personal repositories:

- `~/Projects/IlyasYOY/dotfiles`: Shell config, workstation bootstrap, Homebrew manifests, and terminal or desktop config.
- `~/Projects/IlyasYOY/nvim-workbench`: Neovim configuration, snippets, personal plugin registration, or Neovim runtime checks. Treat the nvim-workbench repo as the target unless the prompt names another path.
- `~/Projects/IlyasYOY/agent-workbench`: Codex config references, custom skills, commands, plugins, or personal agent instructions. Treat the agent-workbench repo as the target unless the prompt names another path.
- `~/Projects/kb-store`: Local storage for creating, editing, searching, reorganizing, summarizing, saving, capturing, or persisting notes for any project. Treat the kb-store repo as the target unless the prompt names another path.
