# Codex Personal Instructions

I'm IlyasYOY (Ilya Ilyinykh, Илья Ильиных), your prompter.

- I speak Russian and English.
- I have a Russian-language blog called kydavoiti.
- I value software quality, explicitness, strictness, and simplicity.

## Instructions

Interactions:

- Deliberate commits: Do not make commits unless I explicitly ask for one.
- Explain: tell me what changed, why it changed, and how it was verified.
- CI-first: Prefer documented Makefile/package targets over ad hoc commands. If a check was not run, say so explicitly.
- If you publish a message on my behalf in a public space, such as GitHub, GitLab, or a wiki, add the following marker on a separate line at the end: "Posted by {Model Name} using Codex". (don't put in commits, there we have co-authored)

Python:

- Use `uv` for Python scripts and ad hoc Python dependencies instead of installing packages into the Homebrew or system Python environment.
- For one-off dependencies, use: `uv run --with <package> python <script.py>`
