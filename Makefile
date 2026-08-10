SHELL_FILES := $(shell find sh -type f -name '*.sh' | sort)

.PHONY: install update update-skills check check-shell check-python check-config

install:
	@./sh/install.sh

update:
	@./sh/update.sh

update-skills:
	@./sh/update-skills.sh

check: check-shell check-python check-config

check-shell:
	@shellcheck $(SHELL_FILES)

check-python:
	@PYTHONPYCACHEPREFIX=/private/tmp/agent-workbench-python-cache \
		python3 -m unittest discover \
		-s config/codex/skills/ai-session-coach/tests -p 'test_*.py'
	@PYTHONPYCACHEPREFIX=/private/tmp/agent-workbench-python-cache \
		python3 -m unittest discover -s tests -p 'test_*.py'

check-config:
	@python3 -c 'import pathlib, tomllib; tomllib.loads(pathlib.Path(".agents/skills/setup-codex/references/config.toml").read_text())'
