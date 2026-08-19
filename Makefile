SHELL_FILES := $(shell find sh -type f -name '*.sh' | sort)

.PHONY: install update update-skills check check-shell check-python check-config check-codex-config

install:
	@./sh/install.sh

update:
	@./sh/update.sh

update-skills:
	@./sh/update-skills.sh

check: check-shell check-python check-config check-codex-config

check-shell:
	@shellcheck $(SHELL_FILES)

check-python:
	@PYTHONPYCACHEPREFIX=/private/tmp/agent-workbench-python-cache \
		python3 -m unittest discover -s tests -p 'test_*.py'

check-config:
	@python3 -c 'import pathlib, tomllib; tomllib.loads(pathlib.Path(".agents/skills/setup-codex/references/config.toml").read_text())'

check-codex-config:
	@uv run --with tomlkit==0.13.3 python -m unittest discover \
		-s .agents/skills/setup-codex/tests -p 'test_*.py'
	@uv run .agents/skills/setup-codex/scripts/normalize_codex_config.py \
		--check .agents/skills/setup-codex/references/config.toml
