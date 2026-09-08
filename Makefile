SHELL_FILES := $(shell find sh -type f -name '*.sh' | sort)
NVIM ?= nvim
NVIM_VERSION ?=
DEPDIR ?= .test-deps
CURL ?= curl -fL --retry 5 --retry-delay 5 --retry-connrefused --create-dirs

ifeq ($(shell uname -s),Darwin)
  ifeq ($(shell uname -m),arm64)
    NVIM_ARCH ?= macos-arm64
  else
    NVIM_ARCH ?= macos-x86_64
  endif
else
  NVIM_ARCH ?= linux-x86_64
endif

ifneq ($(NVIM_VERSION),)
  NVIM_DIR := $(DEPDIR)/nvim-$(NVIM_VERSION)-$(NVIM_ARCH)
  NVIM_STAMP := $(NVIM_DIR)/.installed
  NVIM_TARBALL := $(NVIM_DIR).tar.gz
  NVIM_URL := https://github.com/neovim/neovim/releases/download/$(NVIM_VERSION)/nvim-$(NVIM_ARCH).tar.gz
  CHECK_NVIM := $(abspath $(NVIM_DIR)/nvim-$(NVIM_ARCH)/bin/nvim)
  CHECK_NVIM_DEPS := $(NVIM_STAMP)
else
  CHECK_NVIM := $(NVIM)
  CHECK_NVIM_DEPS :=
endif

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

check-python: $(CHECK_NVIM_DEPS)
	@NVIM="$(CHECK_NVIM)" \
		PYTHONPYCACHEPREFIX=/private/tmp/agent-workbench-python-cache \
		python3 -m unittest discover -s tests -p 'test_*.py'

check-config:
	@python3 -c 'import pathlib, tomllib; tomllib.loads(pathlib.Path(".agents/skills/setup-codex/references/config.toml").read_text())'

check-codex-config:
	@uv run --with tomlkit==0.13.3 python -m unittest discover \
		-s .agents/skills/setup-codex/tests -p 'test_*.py'
	@uv run .agents/skills/setup-codex/scripts/normalize_codex_config.py \
		--check .agents/skills/setup-codex/references/config.toml

ifneq ($(NVIM_VERSION),)
$(NVIM_STAMP):
	$(CURL) "$(NVIM_URL)" -o "$(NVIM_TARBALL)"
	rm -rf "$(NVIM_DIR)"
	mkdir -p "$(NVIM_DIR)"
	tar -xf "$(NVIM_TARBALL)" -C "$(NVIM_DIR)"
	rm -f "$(NVIM_TARBALL)"
	touch "$@"
endif
