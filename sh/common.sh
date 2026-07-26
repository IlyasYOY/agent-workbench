#!/usr/bin/env bash

set -euo pipefail

AGENT_WORKBENCH_DIR=$(realpath "$(dirname "${BASH_SOURCE[0]}")/..")
PERSONAL_PROJECTS_DIR="${ILYASYOY_PERSONAL_PROJECTS_DIR:-$HOME/Projects/IlyasYOY}"
# shellcheck disable=SC2034 # Used by scripts that source this shared file.
LEGACY_DOTFILES_DIR="${ILYASYOY_DOTFILES_DIR:-$PERSONAL_PROJECTS_DIR/dotfiles}"

info() {
    printf "\n\033[1;34m%s\033[0m\n" "$1"
}

success() {
    printf "✅ \033[1;32m%s\033[0m\n" "$1"
}

debug() {
    if [ "${VERBOSE:-0}" = "1" ]; then
        printf "\033[1;37m%s\033[0m\n" "$1"
    fi
}

error() {
    printf "💥 \033[1;31m%s\033[0m\n" "$1"
}

warning() {
    printf "⚠️ \033[1;33m%s\033[0m\n" "$1"
}

confirm_update() {
    local message="$1"
    local answer

    read -r -p "$message [y/n]: " answer
    [[ "$answer" = "y" || "$answer" = "Y" ]]
}

replace_managed_symlink() {
    local target="$1"
    local link="$2"
    shift 2
    local current_target legacy_target

    if [ -L "$link" ]; then
        current_target=$(readlink "$link")
        if [ "$current_target" = "$target" ]; then
            return 0
        fi

        for legacy_target in "$@"; do
            if [ "$current_target" = "$legacy_target" ]; then
                rm -f "$link"
                ln -s "$target" "$link"
                success "Migrated $link -> $target"
                return 0
            fi
        done

        warning "$link points to an unmanaged target; leaving it unchanged"
        return 0
    fi

    if [ -e "$link" ]; then
        warning "$link exists and is not a symlink; leaving it unchanged"
        return 0
    fi

    ln -s "$target" "$link"
    success "Linked $link -> $target"
}

link_skill_tree() {
    local source_root="$1"
    local destination_root="$2"
    local legacy_root="$3"
    local skill_file skill_dir skill_name

    mkdir -p "$destination_root"
    find "$source_root" -mindepth 2 -maxdepth 2 -name SKILL.md -type f -print |
        sort |
        while IFS= read -r skill_file; do
            skill_dir=$(dirname "$skill_file")
            skill_name=$(basename "$skill_dir")
            replace_managed_symlink \
                "$skill_dir" \
                "$destination_root/$skill_name" \
                "$legacy_root/$skill_name"
        done
}

prune_stale_skill_links() {
    local destination_root="$1"
    shift
    local link target

    [ -d "$destination_root" ] || return 0

    find "$destination_root" -mindepth 1 -maxdepth 1 -type l -print |
        sort |
        while IFS= read -r link; do
            target=$(readlink "$link")
            case "$target" in
                "$AGENT_WORKBENCH_DIR"/config/*/skills/*)
                    if [ ! -e "$target" ]; then
                        rm -f "$link"
                        success "Removed stale managed skill link $link"
                    fi
                    ;;
            esac
        done
}

update_workbench_checkout() {
    if [ ! -d "$AGENT_WORKBENCH_DIR/.git" ]; then
        warning "Workbench is not a Git checkout; skipping upstream update"
        return 0
    fi
    if ! git -C "$AGENT_WORKBENCH_DIR" remote get-url origin >/dev/null 2>&1; then
        warning "Workbench has no origin remote; skipping upstream update"
        return 0
    fi
    if [ -n "$(git -C "$AGENT_WORKBENCH_DIR" status --porcelain --untracked-files=all)" ]; then
        warning "Workbench has local changes; skipping upstream update"
        return 0
    fi

    git -C "$AGENT_WORKBENCH_DIR" pull --ff-only
}
