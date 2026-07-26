#!/usr/bin/env bash

set -euo pipefail

# shellcheck disable=SC1091
source "$(dirname "$0")/common.sh"
# shellcheck disable=SC1091
source "$(dirname "$0")/setup/codex-external-skills.sh"

install_codex() {
    local codex_home="${CODEX_HOME:-$HOME/.codex}"
    local namespace="$codex_home/skills/IlyasYOY"

    mkdir -p "$codex_home/rules" "$namespace"
    replace_managed_symlink \
        "$AGENT_WORKBENCH_DIR/config/codex/AGENTS.md" \
        "$codex_home/AGENTS.md" \
        "$LEGACY_DOTFILES_DIR/config/codex/AGENTS.md"
    replace_managed_symlink \
        "$AGENT_WORKBENCH_DIR/config/codex/rules/default.rules" \
        "$codex_home/rules/default.rules" \
        "$LEGACY_DOTFILES_DIR/config/codex/rules/default.rules"

    link_skill_tree \
        "$AGENT_WORKBENCH_DIR/config/agent/skills" \
        "$namespace" \
        "$LEGACY_DOTFILES_DIR/config/agent/skills"
    link_skill_tree \
        "$AGENT_WORKBENCH_DIR/config/codex/skills" \
        "$namespace" \
        "$LEGACY_DOTFILES_DIR/config/codex/skills"
    prune_stale_skill_links "$namespace"

    if [ "${AGENT_WORKBENCH_SKIP_EXTERNAL_SKILLS:-0}" != "1" ]; then
        install_external_codex_skills
    fi
}

install_opencode() {
    local config_home="${XDG_CONFIG_HOME:-$HOME/.config}/opencode"
    local skills="$config_home/skills"

    mkdir -p "$config_home" "$skills"
    replace_managed_symlink \
        "$AGENT_WORKBENCH_DIR/config/opencode/AGENTS.md" \
        "$config_home/AGENTS.md" \
        "$LEGACY_DOTFILES_DIR/config/opencode/AGENTS.md"
    replace_managed_symlink \
        "$AGENT_WORKBENCH_DIR/config/opencode/commands" \
        "$config_home/commands" \
        "$LEGACY_DOTFILES_DIR/config/opencode/commands"
    replace_managed_symlink \
        "$AGENT_WORKBENCH_DIR/config/opencode/plugins" \
        "$config_home/plugins" \
        "$LEGACY_DOTFILES_DIR/config/opencode/plugins"

    link_skill_tree \
        "$AGENT_WORKBENCH_DIR/config/agent/skills" \
        "$skills" \
        "$LEGACY_DOTFILES_DIR/config/agent/skills"
    link_skill_tree \
        "$AGENT_WORKBENCH_DIR/config/opencode/skills" \
        "$skills" \
        "$LEGACY_DOTFILES_DIR/config/opencode/skills"
    prune_stale_skill_links "$skills"
}

info "Installing agent-workbench"
install_codex
install_opencode
success "agent-workbench installed"
info "Run \$setup-codex or \$setup-opencode from $AGENT_WORKBENCH_DIR to review user configuration."
